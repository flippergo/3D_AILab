from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .llm_client import generate_lab_assistant_response
from .schemas import ChatRequest, ChatResponse, FlockingRunRequest, GravityBallRunRequest, MazeAgentRunRequest, SimulationResult
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
SESSION_ID_PATTERN = re.compile(r"[^a-zA-Z0-9_-]")

app = FastAPI(title="3D-AI Lab", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/src", StaticFiles(directory=FRONTEND_DIR / "src"), name="frontend-src")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


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
