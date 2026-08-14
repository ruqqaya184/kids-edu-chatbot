"""
main.py
=========

The FastAPI application: home-screen activity selection, independent
in-memory sessions with a 60-second inactivity timeout, streaming chat
per activity, and per-request monitoring -- all six functional
requirements wired together here.

Run:
    export GEMINI_API_KEY="..."   (or OPENAI_API_KEY)
    uvicorn app.main:app --reload

Then open http://127.0.0.1:8000/docs for the interactive Swagger UI.
"""

import asyncio
import json
import os
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from app.schemas import ChatRequest, ErrorResponse, StartSessionRequest, StartSessionResponse
from app.session_store import (
    active_session_count, append_message, create_session, get_session,
    is_expired, session_exists, sweep_expired_sessions, terminate_session, touch,
)
from app.content_bank import (
    RIDDLES, QUICK_FIRE_QUESTIONS, is_answer_correct, pick_unused_riddle, pick_unused_question,
)
from app.prompts import ACTIVITY_PROMPTS
from app.llm_client import generate_reply_stream
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


# --------------------------------------------------------------------------- #
# Background sweep: server-side enforcement of the 60-second session timeout,
# independent of whether the frontend behaves well (Requirement 2's "no
# session data shall persist after termination" is enforced HERE, not just
# trusted to the client).
# --------------------------------------------------------------------------- #

@app.on_event("startup")
async def start_session_sweeper():
    """Launches a background task that removes expired sessions every 10 seconds for as long as the server runs."""
    async def sweep_loop():
        """Repeatedly removes expired sessions on a fixed interval, forever, for as long as the server runs."""
        interval = int(os.environ.get("SESSION_SWEEP_INTERVAL_SECONDS", "10"))
        while True:
            await asyncio.sleep(interval)
            sweep_expired_sessions()

    asyncio.create_task(sweep_loop())


# --------------------------------------------------------------------------- #
# Structured error handling (same pattern established since Day 11)
# --------------------------------------------------------------------------- #

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Converts any raised HTTPException into a structured ErrorResponse JSON body."""
    error_names = {400: "bad_request", 404: "not_found", 410: "session_expired", 500: "internal_server_error"}
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=error_names.get(exc.status_code, "error"), detail=str(exc.detail)).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catches any exception not already handled and converts it into a structured 500 response."""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(error="internal_server_error", detail=f"An unexpected error occurred: {exc}").model_dump(),
    )


# --------------------------------------------------------------------------- #
# POST /api/session/start
# --------------------------------------------------------------------------- #

@app.post("/api/session/start", response_model=StartSessionResponse, summary="Start a new, independent session for one activity")
def start_session(request: StartSessionRequest):
    """Requirement 2: creates a fresh, independent in-memory session for exactly one activity."""
    session_id = create_session(request.activity)
    return StartSessionResponse(session_id=session_id, activity=request.activity)


# --------------------------------------------------------------------------- #
# DELETE /api/session/{session_id}
# --------------------------------------------------------------------------- #

@app.delete("/api/session/{session_id}", summary="Immediately terminate a session and clear all its data")
def end_session(session_id: str):
    """Called when the user clicks Back, or by the frontend's own 60-second inactivity timer. Requirement 2: no session data shall persist after termination."""
    terminate_session(session_id)
    return {"status": "terminated"}


# --------------------------------------------------------------------------- #
# The activity state machine: builds the next synthetic instruction message
# for the LLM based on the session's current game state and the action the
# user just took. Content selection and correctness grading are
# deterministic (content_bank.py); only the DELIVERY text is generated by
# the LLM, guided by this instruction.
# --------------------------------------------------------------------------- #

def _advance_brain_buster(session: dict, action: str, message: str) -> str:
    """Returns the synthetic instruction text for the LLM's next turn, and mutates session state (current riddle, hints, used set) accordingly."""
    if session["current_index"] is None:
        idx, riddle = pick_unused_riddle(session["used_riddle_indices"])
        if riddle is None:
            return "The riddle bank is empty. Warmly tell the child there are no more riddles right now and congratulate them on playing."
        session["used_riddle_indices"].add(idx)
        session["current_index"] = idx
        session["hints_given"] = 0
        return f'Present this NEW riddle to the child: "{riddle["riddle"]}". Do not reveal the answer.'

    riddle = RIDDLES[session["current_index"]]

    if action == "hint":
        if session["hints_given"] >= 3:
            action = "giveup"  # all hints already used -> treat like a give-up (reveal + move on)
        else:
            session["hints_given"] += 1
            hint_text = riddle["hints"][session["hints_given"] - 1]
            if session["hints_given"] == 3:
                # Per the spec, the answer is revealed after the 3rd hint.
                next_idx, next_riddle = pick_unused_riddle(session["used_riddle_indices"])
                if next_riddle is None:
                    session["current_index"] = None
                    return (f'Give the child this final hint: "{hint_text}". Then reveal that the answer was '
                            f'"{riddle["answers"][0]}", said warmly. Then let them know there are no more riddles '
                            f'right now and congratulate them on playing.')
                session["used_riddle_indices"].add(next_idx)
                session["current_index"] = next_idx
                session["hints_given"] = 0
                return (f'Give the child this final hint: "{hint_text}". Then reveal that the answer was '
                        f'"{riddle["answers"][0]}", said warmly with no negative tone. Then present this NEW riddle: '
                        f'"{next_riddle["riddle"]}". Do not reveal its answer.')
            return f'Give the child this hint (hint #{session["hints_given"]} of 3): "{hint_text}"'

    if action == "giveup":
        answer = riddle["answers"][0]
        next_idx, next_riddle = pick_unused_riddle(session["used_riddle_indices"])
        if next_riddle is None:
            session["current_index"] = None
            return (f'The child gave up. Kindly reveal that the answer was "{answer}", with no negative tone. '
                     'Then let them know there are no more riddles right now and congratulate them on playing.')
        session["used_riddle_indices"].add(next_idx)
        session["current_index"] = next_idx
        session["hints_given"] = 0
        return (f'The child gave up. Kindly reveal that the answer was "{answer}", with no negative tone. '
                f'Then present this NEW riddle: "{next_riddle["riddle"]}". Do not reveal its answer.')

    # action == "answer"
    if is_answer_correct(message or "", riddle["answers"]):
        next_idx, next_riddle = pick_unused_riddle(session["used_riddle_indices"])
        if next_riddle is None:
            session["current_index"] = None
            return ('The child answered CORRECTLY! Celebrate warmly and enthusiastically. Then let them know '
                     "there are no more riddles right now and congratulate them on completing Brain Buster.")
        session["used_riddle_indices"].add(next_idx)
        session["current_index"] = next_idx
        session["hints_given"] = 0
        return (f'The child answered CORRECTLY! Celebrate warmly and enthusiastically (vary your praise). '
                f'Then present this NEW riddle: "{next_riddle["riddle"]}". Do not reveal its answer.')
    else:
        return (f'The child answered INCORRECTLY (they said: "{message}"). Do NOT reveal the answer. '
                 "Respond with warm, gentle encouragement and invite them to try again or ask for a hint.")


def _advance_quick_fire(session: dict, action: str, message: str) -> str:
    """Same pattern as Brain Buster, but for Quick Fire trivia -- no hints, and a short educational fact follows a correct answer."""
    if session["current_index"] is None:
        idx, q = pick_unused_question(session["used_question_indices"])
        if q is None:
            return "The question bank is empty. Warmly tell the child there are no more questions right now and congratulate them on playing."
        session["used_question_indices"].add(idx)
        session["current_index"] = idx
        return f'Present this NEW trivia question to the child (topic: {q["topic"]}): "{q["question"]}"'

    q = QUICK_FIRE_QUESTIONS[session["current_index"]]

    if is_answer_correct(message or "", q["answers"]):
        next_idx, next_q = pick_unused_question(session["used_question_indices"])
        if next_q is None:
            session["current_index"] = None
            return (f'The child answered CORRECTLY! Praise them enthusiastically, then share this fun fact: '
                    f'"{q["fact"]}". Then let them know there are no more questions right now and congratulate '
                    "them on completing Quick Fire.")
        session["used_question_indices"].add(next_idx)
        session["current_index"] = next_idx
        return (f'The child answered CORRECTLY! Praise them enthusiastically (vary your praise), then share this '
                f'fun fact: "{q["fact"]}". Then present this NEW trivia question (topic: {next_q["topic"]}): '
                f'"{next_q["question"]}"')
    else:
        next_idx, next_q = pick_unused_question(session["used_question_indices"])
        if next_q is None:
            session["current_index"] = None
            return (f'The child answered INCORRECTLY. Kindly reveal the correct answer: '
                    f'"{q["correct_answer_display"]}", with warm encouragement. Then let them know there are no '
                    "more questions right now and congratulate them on playing.")
        session["used_question_indices"].add(next_idx)
        session["current_index"] = next_idx
        return (f'The child answered INCORRECTLY (they said: "{message}"). Kindly reveal the correct answer: '
                f'"{q["correct_answer_display"]}", with warm encouragement (never make them feel bad). Then '
                f'present this NEW trivia question (topic: {next_q["topic"]}): "{next_q["question"]}"')


# --------------------------------------------------------------------------- #
# POST /api/chat/stream
# --------------------------------------------------------------------------- #

def _sse_event(data: dict) -> str:
    """Formats one dict as a single Server-Sent Events frame."""
    return f"data: {json.dumps(data)}\n\n"


def _stream_activity_response(session_id: str, activity: str, instruction_text: str, start_time: float, user_prompt_for_log: str):
    """Streams the LLM's reply for one turn as SSE, then logs monitoring data (Requirement 8) once the stream completes."""
    system_prompt = ACTIVITY_PROMPTS[activity]
    history = get_session(session_id)["messages"]
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

    total_ms = (time.perf_counter() - start_time) * 1000
    log_llm_request(
        session_id=session_id, activity=activity, user_prompt=user_prompt_for_log, model=model_used,
        prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, total_tokens=total_tokens,
        ttft_ms=ttft_ms, total_ms=total_ms,
    )

    yield _sse_event({"type": "done"})


@app.post("/api/chat/stream", summary="Send a message/action and stream the activity's reply token-by-token")
def chat_stream(request: ChatRequest):
    """Validates the request, advances the relevant activity's state machine, and streams the LLM's reply back as SSE."""
    start_time = time.perf_counter()

    if not session_exists(request.session_id):
        raise HTTPException(status_code=404, detail="Session not found. It may have expired after 60 seconds of inactivity.")
    if is_expired(request.session_id):
        terminate_session(request.session_id)
        raise HTTPException(status_code=410, detail="Session expired after 60 seconds of inactivity. Please start a new session.")

    if request.action == "answer" and not (request.message or "").strip():
        raise HTTPException(status_code=400, detail="'message' must not be empty for action='answer'.")

    touch(request.session_id)
    session = get_session(request.session_id)
    activity = session["activity"]

    if request.message:
        append_message(request.session_id, "user", request.message)

    if activity == "brain_buster":
        instruction = _advance_brain_buster(session, request.action, request.message or "")
    elif activity == "quick_fire":
        instruction = _advance_quick_fire(session, request.action, request.message or "")
    else:  # ask_explore -- pure open-ended chat, no game state machine
        instruction = request.message or "Greet the child warmly and ask what they're curious about today."

    append_message(request.session_id, "user", instruction)

    return StreamingResponse(
        _stream_activity_response(request.session_id, activity, instruction, start_time, request.message or instruction),
        media_type="text/event-stream",
    )


@app.get("/", summary="Health check")
def root():
    """Health check, also reporting the current number of active sessions."""
    return {"status": "ok", "active_sessions": active_session_count()}
