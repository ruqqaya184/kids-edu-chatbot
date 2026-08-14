# Architecture and Key Design Decisions

## Why Content Is Curated, Not LLM-Improvised

Requirement 7 caps conversation context at the 6 most recent messages.
This means the LLM itself cannot reliably remember which riddles or
questions it already presented once a session runs past a few exchanges
- earlier turns simply fall out of its context window. Trusting the
model's own memory to satisfy "no repeating riddles within the same
session" would therefore be fundamentally unreliable, regardless of how
good the system prompt is.

Instead, content_bank.py holds a fixed, curated bank of 12 riddles and
21 trivia questions (3 per required topic). The SESSION STORE, not the
LLM, tracks which indices have been used per session (used_riddle_indices
/ used_question_indices), guaranteeing no repeats no matter how long the
conversation runs. Correctness grading is also handled in code
(is_answer_correct(), with lenient normalization for children's spelling
and phrasing) rather than trusted to the model's judgment alone.

The LLM is still very much doing real work: it generates the actual
warm, varied, encouraging DELIVERY text around this fixed content -
introducing each riddle, phrasing hints naturally, celebrating correct
answers, and encouraging retries - guided by a synthetic "instruction"
message built by the backend's state machine (_advance_brain_buster /
_advance_quick_fire in main.py) each turn.

## Why a Hybrid Approach, Not Pure LLM Generation

The alternative - asking the LLM to invent riddles/questions and grade
answers entirely on its own - would fail the explicit "no repeats" and
"reveal answer after 3rd hint" requirements as soon as a session exceeds
6 messages, and would produce inconsistent, hard-to-test correctness
grading. The hybrid design keeps the parts that must be reliable
(content selection, no-repeat tracking, correctness checking) fully
deterministic and unit-testable in Python, while keeping the parts that
benefit from an LLM (natural, varied, warm language) genuinely
AI-generated and streamed.

## Dual-Layer Session Timeout Enforcement

Requirement 2's 60-second inactivity timeout is enforced TWICE,
independently:
1. The frontend's useInactivityTimer hook runs its own 60-second timer,
   resetting on every real user interaction, and calls
   DELETE /api/session/{id} + navigates home when it fires.
2. The backend independently enforces the same timeout via
   session_store.is_expired() (checked on every request) and a
   background asyncio task (started in main.py's startup event) that
   sweeps and deletes every expired session every 10 seconds, regardless
   of whether any client ever calls the terminate endpoint.

This was verified with a genuine live test: a real session was created,
the timeout and sweep interval were set to a few seconds via environment
variables, real wall-clock time was allowed to pass, and the session was
confirmed removed automatically with zero client involvement - proving
the server-side guarantee is real, not just theoretical.

## AI Safety: One Shared Preamble, Three Specific Prompts

Requirement 6 asks for each activity to have its own dedicated system
prompt while also enforcing consistent safety behavior. Rather than
writing three separate safety policies (and risking one being weaker or
worded differently), prompts.py defines a single SAFETY_PREAMBLE string
that is prepended to all three activity-specific prompts. This guarantees
identical baseline safety behavior (politely rejecting abuse, refusing
harmful content, redirecting unsafe topics, never asking for personal
information) regardless of which activity a child is using, while still
giving each activity meaningfully different behavioral instructions
beyond that shared baseline.

## Monitoring: Time to First Token, Captured Correctly

Requirement 8 asks for Time to First Token (TTFT) specifically, not just
total response time - a meaningfully different metric that reflects
perceived responsiveness. llm_client.py's generate_reply_stream()
measures wall-clock time from the API call to the FIRST non-empty text
delta arriving, separately from the total time to the last delta. Token
usage is requested via stream_options={"include_usage": True} (with a
graceful retry without that option if a provider rejects it outright),
so real prompt/completion/total token counts are captured even though
the response is streamed - not silently logged as null unless a provider
genuinely doesn't support it.
