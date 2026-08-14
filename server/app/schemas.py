"""
schemas.py
============

Pydantic request/response models for every endpoint.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

Activity = Literal["brain_buster", "quick_fire", "ask_explore"]
ChatAction = Literal["start", "answer", "hint", "giveup"]


class StartSessionRequest(BaseModel):
    """Request body for POST /api/session/start."""
    activity: Activity


class StartSessionResponse(BaseModel):
    """Response body for POST /api/session/start."""
    session_id: str
    activity: Activity


class ChatRequest(BaseModel):
    """
    Request body for POST /api/chat/stream.

    message is required for action="answer" (an attempted riddle/quiz
    answer, or a free-form Ask & Explore question) and ignored for
    action="hint" / action="giveup", which need no text from the user.
    """
    session_id: str
    action: ChatAction = "answer"
    message: Optional[str] = Field(default=None, max_length=1000)


class ErrorResponse(BaseModel):
    error: str
    detail: str
