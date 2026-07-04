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
    simulation_params: dict[str, float | int | bool] | None = None
    experiment_spec: dict[str, Any] | None = None
    codex_task: str | None = None
    assistant_notes: list[str] | None = None


class CodexTaskCreateRequest(BaseModel):
    session_id: str | None = Field(default=None, max_length=80)
    source_message: str = Field(..., min_length=1, max_length=2000)
    experiment_spec: dict[str, Any] = Field(default_factory=dict)
    codex_task: str = Field(..., min_length=1, max_length=10000)


class CodexTaskRecord(BaseModel):
    task_id: str
    created_at: str
    session_id: str
    source_message: str
    simulation_name: str
    title: str
    codex_task: str
    experiment_spec: dict[str, Any]
    status: str = "draft"


class CodexTaskCreateResponse(BaseModel):
    task_id: str
    created_at: str
    status: str
    simulation_name: str
    title: str


class CodexTaskListResponse(BaseModel):
    tasks: list[CodexTaskRecord]


class CodexTaskPlanRequest(BaseModel):
    session_id: str | None = Field(default=None, max_length=80)


class CodexTaskOperation(BaseModel):
    key: str
    label: str
    value: str | list[str]
    target: str


class CodexTaskPlanResponse(BaseModel):
    task_id: str
    status: str
    simulation_name: str
    operations: list[CodexTaskOperation]
    affected_files: list[str]
    warnings: list[str]
    apply_available: bool


class CodexTaskApplyRequest(BaseModel):
    confirm: bool = False


class CodexTaskApplyResponse(BaseModel):
    application_id: str
    applied_at: str
    task_id: str
    simulation_name: str
    status: str
    applied_operations: list[CodexTaskOperation]
    changed_files: list[str]
    result_summary: dict[str, Any]


class CodexTaskImplementationRequestResponse(BaseModel):
    request_id: str
    requested_at: str
    task_id: str
    status: str
    handoff_file: str
    message: str


class CodexImplementationRequestRecord(BaseModel):
    request_id: str
    requested_at: str
    task_id: str
    session_id: str
    simulation_name: str
    title: str
    source_message: str
    codex_task: str
    experiment_spec: dict[str, Any]
    status: str
    handoff_file: str


class CodexImplementationRequestListResponse(BaseModel):
    requests: list[CodexImplementationRequestRecord]


class CodexImplementationStatusResponse(BaseModel):
    task_id: str
    request_id: str | None = None
    status: str
    handoff_file: str | None = None
    output_file: str | None = None
    updated_at: str | None = None
    exit_code: int | None = None
    error: str | None = None
    output_tail: str = ""


class CodexTaskDetailResponse(BaseModel):
    task: CodexTaskRecord
    latest_status: str
    latest_plan: CodexTaskPlanResponse | None = None
    events: list[dict[str, Any]]


class LabResetResponse(BaseModel):
    reset_at: str
    simulations: dict[str, dict[str, Any]]
    changed_files: list[str]
    message: str


class GravityBallRunRequest(BaseModel):
    gravity: float = Field(default=9.8, gt=0, le=50)
    initial_height: float = Field(default=5.0, ge=0.6, le=12)
    bounce: float = Field(default=0.72, ge=0, le=0.98)
    steps: int = Field(default=360, ge=60, le=1200)
    dt: float = Field(default=0.016, gt=0, le=0.1)


class MazeAgentRunRequest(BaseModel):
    grid_size: int = Field(default=7, ge=3, le=25)
    steps_per_cell: int = Field(default=12, ge=1, le=120)
    dt: float = Field(default=0.08, gt=0, le=0.5)
    show_search: bool = False
    randomize: bool = False
    seed: int | None = Field(default=None, ge=0, le=999999)
    wall_density: float = Field(default=0.32, ge=0, le=1)


class FlockingRunRequest(BaseModel):
    agent_count: int = Field(default=30, ge=10, le=80)
    steps: int = Field(default=360, ge=120, le=900)
    dt: float = Field(default=0.08, ge=0.02, le=0.2)
    seed: int | None = Field(default=None, ge=0, le=999999)
    cohesion_weight: float = Field(default=0.55, ge=0, le=2)
    alignment_weight: float = Field(default=0.65, ge=0, le=2)
    separation_weight: float = Field(default=1.25, ge=0, le=3)
    perception_radius: float = Field(default=2.2, ge=0.6, le=5)
    separation_radius: float = Field(default=0.7, ge=0.2, le=2)
    bounds: float = Field(default=6.0, ge=3, le=12)


class SimulationResult(BaseModel):
    meta: dict[str, Any]
    objects: list[dict[str, Any]]
    frames: list[dict[str, Any]]
    summary: dict[str, Any]
