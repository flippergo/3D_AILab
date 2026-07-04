from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .codex_task_apply import apply_codex_task_plan
from .codex_task_apply import append_codex_task_event
from .codex_task_apply import build_codex_task_plan
from .codex_task_apply import ensure_default_customizations
from .codex_task_apply import read_codex_task_events
from .codex_task_apply import reset_lab_runtime_state
from .llm_client import generate_lab_assistant_response
from .schemas import (
    ChatRequest,
    CodexTaskApplyRequest,
    CodexTaskApplyResponse,
    ChatResponse,
    CodexTaskCreateRequest,
    CodexTaskCreateResponse,
    CodexTaskDetailResponse,
    CodexImplementationStatusResponse,
    CodexImplementationRequestListResponse,
    CodexImplementationRequestRecord,
    CodexTaskImplementationRequestResponse,
    CodexTaskListResponse,
    CodexTaskPlanRequest,
    CodexTaskPlanResponse,
    CodexTaskRecord,
    FlockingRunRequest,
    GravityBallRunRequest,
    LabResetResponse,
    MazeAgentRunRequest,
    SimulationResult,
)
from simulations.flocking.sim import FlockingConfig
from simulations.flocking.sim import load_result as load_flocking_result
from simulations.flocking.sim import run_and_save as run_flocking_and_save
from simulations.gravity_ball.sim import GravityBallConfig
from simulations.gravity_ball.sim import load_result as load_gravity_ball_result
from simulations.gravity_ball.sim import run_and_save as run_gravity_ball_and_save
from simulations.maze_agent.sim import MazeAgentConfig
from simulations.maze_agent.sim import load_result as load_maze_agent_result
from simulations.maze_agent.sim import run_and_save as run_maze_agent_and_save

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
LOG_DIR = BASE_DIR / "logs" / "sessions"
EXPERIMENT_LOG_DIR = BASE_DIR / "logs" / "experiments"
CODEX_TASK_LOG_DIR = BASE_DIR / "logs" / "codex_tasks"
CODEX_TASK_LOG_PATH = CODEX_TASK_LOG_DIR / "tasks.jsonl"
CODEX_IMPLEMENTATION_REQUEST_LOG_PATH = CODEX_TASK_LOG_DIR / "implementation_requests.jsonl"
CODEX_IMPLEMENTATION_REQUEST_DIR = CODEX_TASK_LOG_DIR / "pending_implementation"
CODEX_WATCHER_STATE_PATH = CODEX_TASK_LOG_DIR / "watcher_state.json"
SESSION_ID_PATTERN = re.compile(r"[^a-zA-Z0-9_-]")

app = FastAPI(title="3D-AI Lab", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: dict):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store"
        return response


app.mount("/src", NoCacheStaticFiles(directory=FRONTEND_DIR / "src"), name="frontend-src")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html", headers={"Cache-Control": "no-store"})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/lab/reset", response_model=LabResetResponse)
async def reset_lab() -> LabResetResponse:
    return LabResetResponse(**reset_lab_runtime_state())


@app.on_event("startup")
async def startup() -> None:
    ensure_default_customizations()


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    session_id = _safe_session_id(request.session_id)
    timestamp = datetime.now(timezone.utc).isoformat()
    assistant_response = generate_lab_assistant_response(message=message, session_id=session_id)

    _append_session_log(
        session_id=session_id,
        timestamp=timestamp,
        message=message,
        reply=assistant_response.reply,
        suggested_action=assistant_response.suggested_action,
        simulation_params=assistant_response.simulation_params,
        experiment_spec=assistant_response.experiment_spec,
        codex_task=assistant_response.codex_task,
        assistant_notes=assistant_response.assistant_notes,
    )

    return ChatResponse(
        reply=assistant_response.reply,
        session_id=session_id,
        timestamp=timestamp,
        suggested_action=assistant_response.suggested_action,
        simulation_params=assistant_response.simulation_params,
        experiment_spec=assistant_response.experiment_spec,
        codex_task=assistant_response.codex_task,
        assistant_notes=assistant_response.assistant_notes,
    )


@app.post("/codex-tasks", response_model=CodexTaskCreateResponse)
async def create_codex_task(request: CodexTaskCreateRequest) -> CodexTaskCreateResponse:
    session_id = _safe_session_id(request.session_id)
    created_at = datetime.now(timezone.utc).isoformat()
    experiment_spec = request.experiment_spec or {}
    simulation_name = str(experiment_spec.get("simulation_name") or "new_simulation")
    title = str(experiment_spec.get("title") or "Codex依頼案")
    record = CodexTaskRecord(
        task_id=uuid4().hex,
        created_at=created_at,
        session_id=session_id,
        source_message=request.source_message.strip(),
        simulation_name=simulation_name,
        title=title,
        codex_task=request.codex_task.strip(),
        experiment_spec=experiment_spec,
        status="draft",
    )
    _append_codex_task_log(record)
    return CodexTaskCreateResponse(
        task_id=record.task_id,
        created_at=record.created_at,
        status=record.status,
        simulation_name=record.simulation_name,
        title=record.title,
    )


@app.get("/codex-tasks", response_model=CodexTaskListResponse)
async def list_codex_tasks(
    session_id: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> CodexTaskListResponse:
    safe_session_id = _safe_session_id(session_id) if session_id else None
    tasks = _merge_codex_task_statuses(_read_codex_task_logs())
    if safe_session_id:
        tasks = [task for task in tasks if task.session_id == safe_session_id]
    return CodexTaskListResponse(tasks=tasks[:limit])


@app.get("/codex-tasks/{task_id}", response_model=CodexTaskDetailResponse)
async def get_codex_task(task_id: str) -> CodexTaskDetailResponse:
    task = _find_codex_task(task_id)
    events = read_codex_task_events(task_id)
    latest_plan = build_codex_task_plan(task)
    latest_status = events[0].get("status", task.status) if events else task.status
    return CodexTaskDetailResponse(
        task=task,
        latest_status=str(latest_status),
        latest_plan=latest_plan,
        events=events[:10],
    )


@app.post("/codex-tasks/{task_id}/plan", response_model=CodexTaskPlanResponse)
async def plan_codex_task(task_id: str, request: CodexTaskPlanRequest | None = None) -> CodexTaskPlanResponse:
    task = _find_codex_task(task_id)
    if request and request.session_id:
        requested_session_id = _safe_session_id(request.session_id)
        if task.session_id != requested_session_id:
            raise HTTPException(status_code=404, detail="Codex依頼案が見つかりません。")
    return build_codex_task_plan(task)


@app.post("/codex-tasks/{task_id}/apply", response_model=CodexTaskApplyResponse)
async def apply_codex_task(task_id: str, request: CodexTaskApplyRequest) -> CodexTaskApplyResponse:
    if not request.confirm:
        raise HTTPException(status_code=400, detail="適用するには confirm=true が必要です。")

    task = _find_codex_task(task_id)
    plan = build_codex_task_plan(task)
    if not plan.apply_available:
        raise HTTPException(status_code=400, detail="このCodex依頼案は限定適用の対象外です。")

    result = apply_codex_task_plan(task, plan)
    return CodexTaskApplyResponse(**result)


@app.post("/codex-tasks/{task_id}/request-implementation", response_model=CodexTaskImplementationRequestResponse)
async def request_codex_implementation(task_id: str) -> CodexTaskImplementationRequestResponse:
    task = _find_codex_task(task_id)
    record = _append_codex_implementation_request(task)
    return CodexTaskImplementationRequestResponse(
        request_id=record.request_id,
        requested_at=record.requested_at,
        task_id=record.task_id,
        status=record.status,
        handoff_file=record.handoff_file,
        message="Codex実装待ちに追加しました。watcherが起動中なら、このファイルを検出してCodex実装を開始します。",
    )


@app.get("/codex-implementation-requests", response_model=CodexImplementationRequestListResponse)
async def list_codex_implementation_requests(
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> CodexImplementationRequestListResponse:
    requests = _merge_implementation_request_statuses(_read_codex_implementation_requests())
    if status:
        requests = [request for request in requests if request.status == status]
    return CodexImplementationRequestListResponse(requests=requests[:limit])


@app.get("/codex-tasks/{task_id}/implementation-status", response_model=CodexImplementationStatusResponse)
async def get_codex_implementation_status(
    task_id: str,
    tail_chars: int = Query(default=8000, ge=0, le=30000),
) -> CodexImplementationStatusResponse:
    return _get_codex_implementation_status(task_id=task_id, tail_chars=tail_chars)


@app.get("/simulations/gravity_ball/result", response_model=SimulationResult)
async def get_gravity_ball_result() -> dict:
    return load_gravity_ball_result()


@app.post("/simulations/gravity_ball/run", response_model=SimulationResult)
async def run_gravity_ball(request: GravityBallRunRequest) -> dict:
    config = GravityBallConfig(
        gravity=request.gravity,
        initial_height=request.initial_height,
        bounce=request.bounce,
        steps=request.steps,
        dt=request.dt,
    )
    result = run_gravity_ball_and_save(config)
    _append_experiment_log(
        simulation_name="gravity_ball",
        parameters=asdict(config),
        summary=result["summary"],
    )
    return result


@app.get("/simulations/maze_agent/result", response_model=SimulationResult)
async def get_maze_agent_result() -> dict:
    return load_maze_agent_result()


@app.post("/simulations/maze_agent/run", response_model=SimulationResult)
async def run_maze_agent(request: MazeAgentRunRequest) -> dict:
    config = MazeAgentConfig(
        grid_size=request.grid_size,
        steps_per_cell=request.steps_per_cell,
        dt=request.dt,
        show_search=request.show_search,
        randomize=request.randomize,
        seed=request.seed,
        wall_density=request.wall_density,
    )
    result = run_maze_agent_and_save(config)
    _append_experiment_log(
        simulation_name="maze_agent",
        parameters=asdict(config),
        summary=result["summary"],
    )
    return result


@app.get("/simulations/flocking/result", response_model=SimulationResult)
async def get_flocking_result() -> dict:
    return load_flocking_result()


@app.post("/simulations/flocking/run", response_model=SimulationResult)
async def run_flocking(request: FlockingRunRequest) -> dict:
    config = FlockingConfig(
        agent_count=request.agent_count,
        steps=request.steps,
        dt=request.dt,
        seed=request.seed,
        cohesion_weight=request.cohesion_weight,
        alignment_weight=request.alignment_weight,
        separation_weight=request.separation_weight,
        perception_radius=request.perception_radius,
        separation_radius=request.separation_radius,
        bounds=request.bounds,
    )
    result = run_flocking_and_save(config)
    _append_experiment_log(
        simulation_name="flocking",
        parameters=asdict(config),
        summary=result["summary"],
    )
    return result


def _safe_session_id(session_id: str | None) -> str:
    if not session_id:
        return uuid4().hex

    sanitized = SESSION_ID_PATTERN.sub("_", session_id.strip())[:80]
    return sanitized or uuid4().hex


def _find_codex_task(task_id: str) -> CodexTaskRecord:
    for task in _merge_codex_task_statuses(_read_codex_task_logs()):
        if task.task_id == task_id:
            return task
    raise HTTPException(status_code=404, detail="Codex依頼案が見つかりません。")


def _merge_codex_task_statuses(tasks: list[CodexTaskRecord]) -> list[CodexTaskRecord]:
    latest_status_by_task: dict[str, str] = {}
    for event in read_codex_task_events():
        task_id = str(event.get("task_id") or "")
        if task_id and task_id not in latest_status_by_task:
            latest_status_by_task[task_id] = str(event.get("status") or "draft")

    for task in tasks:
        if task.task_id in latest_status_by_task:
            task.status = latest_status_by_task[task.task_id]
    return tasks


def _append_session_log(
    *,
    session_id: str,
    timestamp: str,
    message: str,
    reply: str,
    suggested_action: str | None = None,
    simulation_params: dict[str, float | int | bool] | None = None,
    experiment_spec: dict | None = None,
    codex_task: str | None = None,
    assistant_notes: list[str] | None = None,
) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"session_{session_id}.jsonl"
    record = {
        "timestamp": timestamp,
        "role": "student",
        "message": message,
        "reply": reply,
        "suggested_action": suggested_action,
        "simulation_params": simulation_params,
        "experiment_spec": experiment_spec,
        "codex_task": codex_task,
        "assistant_notes": assistant_notes,
    }

    with log_path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(record, ensure_ascii=False) + "\n")


def _append_experiment_log(
    *,
    simulation_name: str,
    parameters: dict,
    summary: dict,
) -> None:
    EXPERIMENT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = EXPERIMENT_LOG_DIR / f"{simulation_name}.jsonl"
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "simulation_name": simulation_name,
        "parameters": parameters,
        "summary": summary,
    }

    with log_path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(record, ensure_ascii=False) + "\n")


def _append_codex_task_log(record: CodexTaskRecord) -> None:
    CODEX_TASK_LOG_DIR.mkdir(parents=True, exist_ok=True)
    payload = record.model_dump() if hasattr(record, "model_dump") else record.dict()
    with CODEX_TASK_LOG_PATH.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _append_codex_implementation_request(task: CodexTaskRecord) -> CodexImplementationRequestRecord:
    requested_at = datetime.now(timezone.utc).isoformat()
    request_id = uuid4().hex
    CODEX_IMPLEMENTATION_REQUEST_DIR.mkdir(parents=True, exist_ok=True)
    handoff_path = CODEX_IMPLEMENTATION_REQUEST_DIR / f"{requested_at.replace(':', '').replace('+', 'Z')}_{task.task_id}.md"
    handoff_text = _format_codex_handoff(task=task, request_id=request_id, requested_at=requested_at)
    handoff_path.write_text(handoff_text, encoding="utf-8")
    record = CodexImplementationRequestRecord(
        request_id=request_id,
        requested_at=requested_at,
        task_id=task.task_id,
        session_id=task.session_id,
        simulation_name=task.simulation_name,
        title=task.title,
        source_message=task.source_message,
        codex_task=task.codex_task,
        experiment_spec=task.experiment_spec,
        status="pending",
        handoff_file=str(handoff_path.relative_to(BASE_DIR)),
    )
    CODEX_TASK_LOG_DIR.mkdir(parents=True, exist_ok=True)
    payload = record.model_dump() if hasattr(record, "model_dump") else record.dict()
    with CODEX_IMPLEMENTATION_REQUEST_LOG_PATH.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(payload, ensure_ascii=False) + "\n")
    append_codex_task_event(
        {
            "event_id": request_id,
            "event_type": "implementation_requested",
            "created_at": requested_at,
            "task_id": task.task_id,
            "simulation_name": task.simulation_name,
            "status": "implementation_requested",
            "handoff_file": record.handoff_file,
        }
    )
    return record


def _format_codex_handoff(*, task: CodexTaskRecord, request_id: str, requested_at: str) -> str:
    experiment_spec = json.dumps(task.experiment_spec, ensure_ascii=False, indent=2)
    return f"""# Codex実装依頼

- request_id: {request_id}
- requested_at: {requested_at}
- task_id: {task.task_id}
- session_id: {task.session_id}
- simulation_name: {task.simulation_name}
- title: {task.title}
- status: pending

## 元メッセージ

{task.source_message}

## 実験・機能仕様

```json
{experiment_spec}
```

## Codex向けタスク文

{task.codex_task}

## 実装時の注意

- 既存の3D表示、チャット、シミュレーション操作、初期状態ボタンを壊さないこと。
- 実装後に構文確認と必要なAPI/UI確認を行うこと。
- サーバー側から任意コマンド実行やGit操作を自動実行しないこと。
"""


def _read_codex_implementation_requests() -> list[CodexImplementationRequestRecord]:
    if not CODEX_IMPLEMENTATION_REQUEST_LOG_PATH.exists():
        return []

    requests: list[CodexImplementationRequestRecord] = []
    with CODEX_IMPLEMENTATION_REQUEST_LOG_PATH.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                requests.append(CodexImplementationRequestRecord(**json.loads(line)))
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
    return sorted(requests, key=lambda request: request.requested_at, reverse=True)


def _merge_implementation_request_statuses(
    requests: list[CodexImplementationRequestRecord],
) -> list[CodexImplementationRequestRecord]:
    state = _read_watcher_state()
    for request in requests:
        watcher_record = state.get(request.handoff_file) or state.get(str(Path(request.handoff_file)))
        if watcher_record:
            request.status = str(watcher_record.get("status") or request.status)
    return requests


def _get_codex_implementation_status(*, task_id: str, tail_chars: int) -> CodexImplementationStatusResponse:
    requests = [request for request in _merge_implementation_request_statuses(_read_codex_implementation_requests()) if request.task_id == task_id]
    if not requests:
        return CodexImplementationStatusResponse(task_id=task_id, status="not_requested")

    request = requests[0]
    state = _read_watcher_state()
    watcher_record = state.get(request.handoff_file) or state.get(str(Path(request.handoff_file)))
    status = request.status
    output_file = None
    updated_at = None
    exit_code = None
    error = None
    output_tail = ""

    if watcher_record:
        status = str(watcher_record.get("status") or status)
        output_file = watcher_record.get("output_file")
        updated_at = watcher_record.get("updated_at")
        exit_code = watcher_record.get("exit_code")
        error = watcher_record.get("error")
        if output_file:
            output_tail = _read_relative_text_tail(str(output_file), tail_chars)

    return CodexImplementationStatusResponse(
        task_id=task_id,
        request_id=request.request_id,
        status=status,
        handoff_file=request.handoff_file,
        output_file=output_file,
        updated_at=updated_at,
        exit_code=exit_code,
        error=error,
        output_tail=output_tail,
    )


def _read_watcher_state() -> dict[str, dict[str, Any]]:
    if not CODEX_WATCHER_STATE_PATH.exists():
        return {}
    try:
        payload = json.loads(CODEX_WATCHER_STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_relative_text_tail(relative_path: str, tail_chars: int) -> str:
    if tail_chars <= 0:
        return ""
    path = (BASE_DIR / relative_path).resolve()
    try:
        path.relative_to(BASE_DIR.resolve())
    except ValueError:
        return ""
    if not path.exists() or not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return text[-tail_chars:]


def _read_codex_task_logs() -> list[CodexTaskRecord]:
    if not CODEX_TASK_LOG_PATH.exists():
        return []

    tasks: list[CodexTaskRecord] = []
    with CODEX_TASK_LOG_PATH.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                tasks.append(CodexTaskRecord(**json.loads(line)))
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
    return sorted(tasks, key=lambda task: task.created_at, reverse=True)
