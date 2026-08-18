"""
llm_client.py
===============

Shared client, extended from the pattern used since Day 8: auto-detects
whichever API key is set (OPENAI_API_KEY or GEMINI_API_KEY) and routes
accordingly, since Gemini exposes an OpenAI-compatible endpoint that
accepts the same openai Python SDK -- this project uses Gemini's free
tier via that compatibility layer, per this project's explicit choice.

Extended for Day 14's monitoring requirement (Requirement 8): the
streaming generator now measures and yields Time to First Token (TTFT)
and attempts to capture real token usage even while streaming, via
stream_options={"include_usage": True} -- a real OpenAI/Gemini feature
that requests a final usage-only chunk at the end of the stream. If a
provider doesn't support this option, usage is logged as None rather
than guessed at (see monitoring.py).
"""

import os
import time

from dotenv import load_dotenv

load_dotenv()


def get_client_and_model():
    """Returns (client, model_name, provider_label), preferring OPENAI_API_KEY, falling back to GEMINI_API_KEY via Google's OpenAI-compatible endpoint."""
    from openai import OpenAI

    openai_key = os.environ.get("OPENAI_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")

    if openai_key:
        return OpenAI(), "gpt-4o-mini", "OpenAI"

    if gemini_key:
        client = OpenAI(
            api_key=gemini_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        return client, "gemini-flash-lite-latest", "Gemini (via OpenAI-compatible endpoint)"

    raise RuntimeError(
        "Neither OPENAI_API_KEY nor GEMINI_API_KEY is set. Set one with:\n"
        '  export OPENAI_API_KEY="sk-..."       (real OpenAI key)\n'
        '  export GEMINI_API_KEY="..."          (free key from https://aistudio.google.com/apikey)'
    )


def generate_reply_stream(messages: list, temperature: float = 0.8, max_tokens: int = 300):
    """
    Streams a reply and yields structured events for the caller to both
    forward to the browser AND use for monitoring (Requirement 8):
        {"type": "delta", "text": "..."}                          -- one per token/chunk
        {"type": "done", "full_text": ..., "model": ..., "ttft_ms": ...,
         "total_ms": ..., "prompt_tokens": ..., "completion_tokens": ...,
         "total_tokens": ...}                                       -- exactly once, at the end

    TTFT (Time to First Token) is measured as the wall-clock time between
    calling the API and the FIRST non-empty text delta arriving -- the
    metric that actually reflects perceived responsiveness to the user,
    distinct from total generation time.
    """
    client, model, provider_label = get_client_and_model()
    start_time = time.perf_counter()
    first_token_time = None

    prompt_tokens = completion_tokens = total_tokens = None

    try:
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            stream_options={"include_usage": True},
        )
    except Exception:
        # Some providers reject unknown stream_options outright rather
        # than ignoring them -- retry once without it rather than failing
        # the whole request over an optional monitoring enhancement.
        stream = client.chat.completions.create(
            model=model, messages=messages, temperature=temperature,
            max_tokens=max_tokens, stream=True,
        )

    full_text = ""
    for event in stream:
        usage = getattr(event, "usage", None)
        if usage is not None:
            prompt_tokens = getattr(usage, "prompt_tokens", None)
            completion_tokens = getattr(usage, "completion_tokens", None)
            total_tokens = getattr(usage, "total_tokens", None)

        if not event.choices:
            continue
        delta = event.choices[0].delta.content
        if delta:
            if first_token_time is None:
                first_token_time = time.perf_counter()
            full_text += delta
            yield {"type": "delta", "text": delta}

    end_time = time.perf_counter()
    ttft_ms = (first_token_time - start_time) * 1000 if first_token_time else None
    total_ms = (end_time - start_time) * 1000

    yield {
        "type": "done",
        "full_text": full_text,
        "model": model,
        "provider": provider_label,
        "ttft_ms": ttft_ms,
        "total_ms": total_ms,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


def generate_reply_once(messages: list, temperature: float = 0.0, max_tokens: int = 150) -> str:
    """
    Non-streaming, single-shot completion -- used for the hidden state-
    extraction call (see prompts.py's STATE_EXTRACTION_PROMPT), not shown
    to the user. temperature=0.0 since we want consistent, literal
    extraction here, not creative variation.
    """
    client, model, _ = get_client_and_model()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""