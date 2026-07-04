from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, max_length=80)


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    timestamp: str
    suggested_action: str | None = None
    simulation_params: dict[str, float | int] | None = None
    experiment_spec: dict[str, Any] | None = None
    codex_task: str | None = None
    assistant_notes: list[str] | None = None


class GravityBallRunRequest(BaseModel):
    gravity: float = Field(default=9.8, gt=0, le=50)
    initial_height: float = Field(default=5.0, ge=0.6, le=12)
    bounce: float = Field(default=0.72, ge=0, le=0.98)
    steps: int = Field(default=360, ge=60, le=1200)
    dt: float = Field(default=0.016, gt=0, le=0.1)


class SimulationResult(BaseModel):
    meta: dict[str, Any]
    objects: list[dict[str, Any]]
    frames: list[dict[str, Any]]
    summary: dict[str, Any]
