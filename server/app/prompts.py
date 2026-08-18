"""
prompts.py
===========

Loads each activity's system prompt from its own markdown file in
app/prompts/, and combines it with the shared safety preamble
(app/prompts/common_safety.md). Splitting these into separate files
keeps each activity's instructions easy to review and edit on their
own, independent of the Python code that uses them.

STATE_EXTRACTION_PROMPT stays defined here directly rather than as a
markdown file, since it's an internal plumbing prompt (used for the
hidden state-tracking call in main.py) rather than user-facing
activity content -- see main.py's _extract_state() for how it's used.
"""

import os

_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")


def _read(filename: str) -> str:
    path = os.path.join(_PROMPTS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


_SAFETY_PREAMBLE = _read("common_safety.md")

BRAIN_BUSTER_PROMPT = _SAFETY_PREAMBLE + "\n\n" + _read("brain_buster.md")
QUICK_FIRE_PROMPT = _SAFETY_PREAMBLE + "\n\n" + _read("quick_fire.md")
ASK_EXPLORE_PROMPT = _SAFETY_PREAMBLE + "\n\n" + _read("ask_explore.md")

ACTIVITY_PROMPTS = {
    "brain_buster": BRAIN_BUSTER_PROMPT,
    "quick_fire": QUICK_FIRE_PROMPT,
    "ask_explore": ASK_EXPLORE_PROMPT,
}


STATE_EXTRACTION_PROMPT = """You will be shown the most recent assistant reply from an educational game for children (either a riddle game or a trivia game).

Read it and output ONLY a single JSON object, nothing else, no markdown formatting, no explanation, in exactly this shape:

{"active_prompt": "<the exact riddle or trivia question text currently awaiting an answer, or null if none is currently active (e.g. the reply just revealed an answer and moved on without yet stating a new one, or it's a closing message)>", "topic": "<a short 1-3 word topic/theme label for the CURRENT or just-completed riddle/question, e.g. \\"kitchen object\\", \\"space\\", \\"animals\\", or null if not applicable>"}

Output ONLY the JSON object."""