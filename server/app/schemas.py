"""
schemas.py
============
Pydantic request/response models for every endpoint.
"""
from typing import Optional
from pydantic import BaseModel, Field
from typing import Literal

Activity = Literal["brain_buster", "quick_fire", "ask_explore"]


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

    message is the child's plain-text message for this turn -- whatever
    they typed, or whatever a UI button (Hint / Give Up) sends as a
    plain-language message (e.g. "Can I get a hint?"). There is no more
    special 'action' field: the LLM itself determines what kind of
    message it received (a guess, a hint request, a give-up, an
    open-ended question) from the message content and the system prompt,
    rather than the backend branching on a fixed action type.
    """
    session_id: str
    message: Optional[str] = Field(default=None, max_length=1000)


class ErrorResponse(BaseModel):
    error: str
    detail: str