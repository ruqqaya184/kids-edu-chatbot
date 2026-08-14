"""
monitoring.py
===============

Requirement 8: for every LLM request, record timestamp, session ID,
activity name, user prompt, input/output/total token usage, Time to
First Token (TTFT), and total response generation time -- to a DEDICATED
log file, separate from any general application logs, so monitoring data
can be inspected, parsed, or fed into an analytics pipeline independently
of ordinary server logs (startup messages, request routing, etc.).
"""

import json
import logging
import os
from datetime import datetime, timezone

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
MONITORING_LOG_FILE = os.path.join(LOG_DIR, "monitoring.log")

_monitoring_logger = None


def get_monitoring_logger() -> logging.Logger:
    """Creates (or returns) a logger dedicated ONLY to LLM-request monitoring, writing JSON lines to logs/monitoring.log and nowhere else."""
    global _monitoring_logger
    if _monitoring_logger is not None:
        return _monitoring_logger

    logger = logging.getLogger("llm_monitoring")
    logger.setLevel(logging.INFO)
    logger.propagate = False  # keep this fully separate from the root/app logger

    handler = logging.FileHandler(MONITORING_LOG_FILE)
    handler.setFormatter(logging.Formatter("%(message)s"))  # each line is already a full JSON object
    logger.addHandler(handler)

    _monitoring_logger = logger
    return logger


def log_llm_request(session_id: str, activity: str, user_prompt: str, model: str,
                     prompt_tokens, completion_tokens, total_tokens,
                     ttft_ms, total_ms: float) -> None:
    """
    Writes exactly one JSON line per LLM request with every field
    Requirement 8 asks for. Numeric fields are rounded for readability;
    None values (e.g. token usage the provider didn't report) are
    preserved as JSON null rather than a misleading 0.
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "activity": activity,
        "user_prompt": user_prompt,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "ttft_ms": round(ttft_ms, 2) if ttft_ms is not None else None,
        "total_response_time_ms": round(total_ms, 2),
    }
    get_monitoring_logger().info(json.dumps(entry))
