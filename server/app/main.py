"""
main.py
=========

The FastAPI application: home-screen activity selection, independent
in-memory sessions with a 60-second inactivity timeout, streaming chat
per activity, and per-request monitoring.

UPDATED: riddles/trivia questions are now invented by the LLM itself,
and the LLM grades the child's answers itself -- nothing is pulled from
a static content bank anymore. A lightweight "session state" (current
riddle/question text + topics already used) is tracked server-side and
re-injected into the system prompt every turn, so the LLM has reliable
memory of its own prior content even though raw conversation history is
capped at 6 messages. See app/prompts.py for the full explanation.

Run:
    export GEMINI_API_KEY="..."   (or OPENAI_API_KEY)
    uvicorn app.main:app --reload

Then open http://127.0.0.1:8000/docs for the interactive Swagger UI.
"""

import asyncio
import json
import os
import re
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from app.schemas import ChatRequest, ErrorResponse, StartSessionRequest, StartSessionResponse
from app.session_store import (
    active_session_count, append_message, create_session, get_session,
    is_expired, session_exists, sweep_expired_sessions, terminate_session, touch,
)
from app.prompts import ACTIVITY_PROMPTS, STATE_EXTRACTION_PROMPT
from app.llm_client import generate_reply_stream, generate_reply_once
from app.monitoring import log_llm_request

app = FastAPI(
    title="Day 14 - Kids Educational Chatbot",
    description="Brain Buster, Quick Fire, and Ask & Explore -- a full-stack educational chatbot for children.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def start_session_sweeper():
    """Launches a background task that removes expired sessions every 10 seconds for as long as the server runs."""
    async def sweep_loop():
        interval = int(os.environ.get("SESSION_SWEEP_INTERVAL_SECONDS", "10"))
        while True:
            await asyncio.sleep(interval)
            sweep_expired_sessions()

    asyncio.create_task(sweep_loop())


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    error_names = {400: "bad_request", 404: "not_found", 410: "session_expired", 500: "internal_server_error"}
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=error_names.get(exc.status_code, "error"), detail=str(exc.detail)).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(error="internal_server_error", detail=f"An unexpected error occurred: {exc}").model_dump(),
    )


@app.post("/api/session/start", response_model=StartSessionResponse, summary="Start a new, independent session for one activity")
def start_session(request: StartSessionRequest):
    session_id = create_session(request.activity)
    return StartSessionResponse(session_id=session_id, activity=request.activity)


@app.delete("/api/session/{session_id}", summary="Immediately terminate a session and clear all its data")
def end_session(session_id: str):
    terminate_session(session_id)
    return {"status": "terminated"}


# --------------------------------------------------------------------------- #
# Session game-state helpers (replaces the old content_bank-driven state
# machine). Stored directly on the session dict, lazily initialized.
# --------------------------------------------------------------------------- #

MAX_TRACKED_TOPICS = 15  # avoid an unbounded list over a very long session


def _get_game_state(session: dict) -> dict:
    """Lazily initializes and returns this session's game_state dict."""
    return session.setdefault("game_state", {"active_prompt": None, "topics_used": [], "hints_given": 0})

def _build_state_context(activity: str, game_state: dict) -> str:
    """
    Builds the 'Current session state' note re-injected into the system
    prompt every turn, giving the LLM reliable memory of its own current
    riddle/question, recently used topics, and (for Brain Buster) how many
    hints have already been given for the current riddle -- independent
    of whether raw conversation history has scrolled past the 6-message
    cap.
    """
    if activity == "ask_explore":
        return ""  # no game state for open-ended chat

    active = game_state.get("active_prompt")
    topics = game_state.get("topics_used", [])

    lines = ["Current session state:"]
    if active:
        lines.append(f'- The riddle/question currently awaiting an answer is: "{active}"')
    else:
        lines.append("- There is no riddle/question currently active. Present a new one.")
    if topics:
        lines.append(f"- Topics already used this session (avoid repeating): {', '.join(topics)}")

    if activity == "brain_buster" and active:
        hints_given = game_state.get("hints_given", 0)
        lines.append(f"- Hints given so far for the current riddle: {hints_given} (maximum allowed is 3)")

    return "\n".join(lines)


def _extract_state(assistant_reply: str) -> dict:
    """
    Hidden, non-streamed follow-up call: asks the LLM to summarize its own
    just-given reply into structured state (current active riddle/question
    text, topic label, and whether a hint was just given), so we can store
    and re-inject it next turn. This runs AFTER the visible streamed reply
    has already fully reached the browser -- it never blocks or delays
    what the child sees. Falls back to a safe empty state if the model's
    output isn't valid JSON -- this must never crash the main chat flow.
    """
    try:
        raw = generate_reply_once([
            {"role": "system", "content": STATE_EXTRACTION_PROMPT},
            {"role": "user", "content": assistant_reply},
        ])
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return {"active_prompt": None, "topic": None, "hint_given": False}
        parsed = json.loads(match.group(0))
        return {
            "active_prompt": parsed.get("active_prompt"),
            "topic": parsed.get("topic"),
            "hint_given": bool(parsed.get("hint_given", False)),
        }
    except Exception:
        # State extraction is a best-effort memory aid, not a critical
        # path -- if it fails for any reason, the game continues with no
        # remembered state rather than crashing the request.
        return {"active_prompt": None, "topic": None, "hint_given": False}


# --------------------------------------------------------------------------- #
# POST /api/chat/stream
# --------------------------------------------------------------------------- #

def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def _stream_activity_response(session_id: str, activity: str, start_time: float, user_message_for_log: str):
    """
    Streams the LLM's reply as SSE -- THIS STREAMING LOOP IS UNCHANGED FROM
    BEFORE. The LLM invents/grades content itself, guided only by the
    system prompt + freshly-built state context -- no synthetic 'the child
    answered correctly' instruction is injected anymore. After the visible
    reply has fully streamed to the browser, a hidden non-streamed
    follow-up call extracts updated state (see _extract_state) before
    logging -- this happens after streaming is already complete, so it
    never affects the streamed response itself.
    """
    session = get_session(session_id)
    game_state = _get_game_state(session)

    system_prompt = ACTIVITY_PROMPTS[activity]
    state_context = _build_state_context(activity, game_state)
    if state_context:
        system_prompt = f"{system_prompt}\n\n{state_context}"

    history = session["messages"]
    messages = [{"role": "system", "content": system_prompt}] + history

    full_text = ""
    model_used = "unknown"
    ttft_ms = None
    prompt_tokens = completion_tokens = total_tokens = None

    try:
        for chunk in generate_reply_stream(messages):
            if chunk["type"] == "delta":
                full_text += chunk["text"]
                yield _sse_event({"type": "delta", "text": chunk["text"]})
            elif chunk["type"] == "done":
                model_used = chunk["model"]
                ttft_ms = chunk["ttft_ms"]
                prompt_tokens = chunk["prompt_tokens"]
                completion_tokens = chunk["completion_tokens"]
                total_tokens = chunk["total_tokens"]
    except Exception as e:
        yield _sse_event({"type": "error", "detail": f"The language model request failed: {e}"})
        return

    if session_exists(session_id):
        append_message(session_id, "assistant", full_text)

        # Hidden follow-up call: update this session's remembered state.
        # Runs after streaming is fully done -- does not affect the
        # response the child already received.
               # Hidden follow-up call: update this session's remembered state.
        # Runs after streaming is fully done -- does not affect the
        # response the child already received.
        if activity != "ask_explore":
            previous_active_prompt = game_state.get("active_prompt")
            extracted = _extract_state(full_text)
            new_active_prompt = extracted.get("active_prompt")

            game_state["active_prompt"] = new_active_prompt
            topic = extracted.get("topic")
            if topic and topic not in game_state["topics_used"]:
                game_state["topics_used"].append(topic)
                game_state["topics_used"] = game_state["topics_used"][-MAX_TRACKED_TOPICS:]

            if activity == "brain_buster":
                if new_active_prompt != previous_active_prompt:
                    # A new riddle started (or the old one was resolved) --
                    # reset the hint counter for the fresh riddle.
                    game_state["hints_given"] = 0
                elif extracted.get("hint_given"):
                    game_state["hints_given"] = game_state.get("hints_given", 0) + 1

    total_ms = (time.perf_counter() - start_time) * 1000
    log_llm_request(
        session_id=session_id, activity=activity, user_prompt=user_message_for_log, model=model_used,
        prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, total_tokens=total_tokens,
        ttft_ms=ttft_ms, total_ms=total_ms,
    )

    yield _sse_event({"type": "done"})


@app.post("/api/chat/stream", summary="Send a message/action and stream the activity's reply token-by-token")
def chat_stream(request: ChatRequest):
    """
    Validates the request and streams the LLM's reply back as SSE. The
    child's message (whatever they typed, or whatever a UI button sent as
    plain text, e.g. "Can I get a hint?") is forwarded to the LLM as-is --
    there is no more special-cased action branching for hint/giveup/answer.
    The LLM itself decides what kind of message it received and how to
    respond, guided by the system prompt.
    """
    start_time = time.perf_counter()

    if not session_exists(request.session_id):
        raise HTTPException(status_code=404, detail="Session not found. It may have expired after 60 seconds of inactivity.")
    if is_expired(request.session_id):
        terminate_session(request.session_id)
        raise HTTPException(status_code=410, detail="Session expired after 60 seconds of inactivity. Please start a new session.")

    touch(request.session_id)
    session = get_session(request.session_id)
    activity = session["activity"]

    user_message = (request.message or "").strip()

    if user_message:
        append_message(request.session_id, "user", user_message)
    elif not session["messages"]:
        # First turn of the session with no message yet (e.g. frontend
        # just opened the activity) -- nudge the LLM to open with a
        # greeting + first riddle/question, per each prompt's instructions.
        append_message(request.session_id, "user", "(The child just opened this activity. Greet them and begin.)")

    return StreamingResponse(
        _stream_activity_response(request.session_id, activity, start_time, user_message),
        media_type="text/event-stream",
    )


@app.get("/", summary="Health check")
def root():
    return {"status": "ok", "active_sessions": active_session_count()}