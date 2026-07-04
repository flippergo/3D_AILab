from __future__ import annotations

import json
import os
import re
import shutil
import unicodedata
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .schemas import CodexTaskOperation, CodexTaskPlanResponse, CodexTaskRecord
from simulations.flocking.sim import FlockingConfig
from simulations.flocking.sim import run_and_save as run_flocking_and_save
from simulations.gravity_ball.sim import GravityBallConfig
from simulations.gravity_ball.sim import run_and_save as run_gravity_ball_and_save
from simulations.maze_agent.sim import MazeAgentConfig
from simulations.maze_agent.sim import run_and_save as run_maze_agent_and_save

BASE_DIR = Path(__file__).resolve().parent.parent
CODEX_TASK_DIR = BASE_DIR / "logs" / "codex_tasks"
EVENT_LOG_PATH = CODEX_TASK_DIR / "events.jsonl"
IMPLEMENTATION_REQUEST_LOG_PATH = CODEX_TASK_DIR / "implementation_requests.jsonl"
PENDING_IMPLEMENTATION_DIR = CODEX_TASK_DIR / "pending_implementation"
WATCHER_OUTPUT_DIR = CODEX_TASK_DIR / "watcher_outputs"
WATCHER_STATE_PATH = CODEX_TASK_DIR / "watcher_state.json"
WATCHER_LOCK_PATH = CODEX_TASK_DIR / "watcher.lock"

SIMULATION_DIRS = {
    "gravity_ball": BASE_DIR / "simulations" / "gravity_ball",
    "maze_agent": BASE_DIR / "simulations" / "maze_agent",
    "flocking": BASE_DIR / "simulations" / "flocking",
}

DEFAULT_VISUALS = {
    "gravity_ball": {
        "ball_color": "#ffd166",
        "floor_color": "#1a222b",
        "trajectory_color": "#ffd166",
    },
    "maze_agent": {
        "floor_color": "#1b242d",
        "path_color": "#45c4a0",
        "start_color": "#65d46e",
        "goal_color": "#ffd166",
        "agent_color": "#72a7ff",
        "wall_color": "#566273",
    },
    "flocking": {
        "agent_palette": ["#8fd3ff", "#ffd166", "#45c4a0"],
        "bounds_color": "#45c4a0",
    },
}

COLOR_NAMES = {
    "red": "#e85d5d",
    "赤": "#e85d5d",
    "blue": "#5d8fe8",
    "青": "#5d8fe8",
    "green": "#45c4a0",
    "緑": "#45c4a0",
    "yellow": "#ffd166",
    "黄色": "#ffd166",
    "orange": "#f59f4c",
    "オレンジ": "#f59f4c",
    "purple": "#a985ff",
    "紫": "#a985ff",
    "pink": "#ff8ab3",
    "ピンク": "#ff8ab3",
    "white": "#f2f5f7",
    "白": "#f2f5f7",
    "black": "#111820",
    "黒": "#111820",
    "gray": "#697586",
    "grey": "#697586",
    "グレー": "#697586",
    "灰色": "#697586",
    "cyan": "#8fd3ff",
    "水色": "#8fd3ff",
    "teal": "#45c4a0",
}

HEX_COLOR_PATTERN = re.compile(r"#[0-9a-fA-F]{6}")


def build_codex_task_plan(task: CodexTaskRecord) -> CodexTaskPlanResponse:
    simulation_name = _detect_simulation_name(task)
    warnings: list[str] = []
    if simulation_name not in SIMULATION_DIRS:
        return _unsupported_plan(
            task,
            simulation_name=simulation_name,
            warning="限定適用できる対象は gravity_ball, maze_agent, flocking だけです。",
        )

    text = _task_text(task)
    color = _extract_color(text)
    if color is None:
        return _unsupported_plan(
            task,
            simulation_name=simulation_name,
            warning="変更する色を読み取れませんでした。例: maze_agentの壁を赤くしたい",
        )

    operations = _detect_operations(simulation_name, text, color)
    if not operations:
        return _unsupported_plan(
            task,
            simulation_name=simulation_name,
            warning="変更対象を読み取れませんでした。例: 壁、ボール、床、経路、個体、境界線",
        )

    return CodexTaskPlanResponse(
        task_id=task.task_id,
        status="ready",
        simulation_name=simulation_name,
        operations=operations,
        affected_files=_affected_files(simulation_name),
        warnings=warnings,
        apply_available=True,
    )


def apply_codex_task_plan(task: CodexTaskRecord, plan: CodexTaskPlanResponse) -> dict:
    if plan.status != "ready" or not plan.apply_available:
        raise ValueError("適用できるCodex依頼案ではありません。")

    simulation_dir = SIMULATION_DIRS[plan.simulation_name]
    customization_path = simulation_dir / "customization.json"
    customization = _read_customization(plan.simulation_name, customization_path)
    visuals = customization.setdefault("visuals", {})

    for operation in plan.operations:
        visuals[operation.key] = operation.value

    _write_customization(customization_path, customization)
    result = _run_simulation(plan.simulation_name)
    application_id = uuid4().hex
    applied_at = datetime.now(timezone.utc).isoformat()
    readme_path = simulation_dir / "README.md"
    _update_simulation_readme(readme_path, applied_at, plan.operations)
    changed_files = [
        str(customization_path.relative_to(BASE_DIR)),
        str((simulation_dir / "result.json").relative_to(BASE_DIR)),
        str(readme_path.relative_to(BASE_DIR)),
    ]
    event = {
        "event_id": application_id,
        "event_type": "applied",
        "created_at": applied_at,
        "task_id": task.task_id,
        "simulation_name": plan.simulation_name,
        "status": "applied",
        "operations": [_model_dump(operation) for operation in plan.operations],
        "changed_files": changed_files,
        "result_summary": result.get("summary", {}),
    }
    append_codex_task_event(event)
    return {
        "application_id": application_id,
        "applied_at": applied_at,
        "task_id": task.task_id,
        "simulation_name": plan.simulation_name,
        "status": "applied",
        "applied_operations": plan.operations,
        "changed_files": changed_files,
        "result_summary": result.get("summary", {}),
    }


def append_codex_task_event(event: dict) -> None:
    EVENT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVENT_LOG_PATH.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(event, ensure_ascii=False) + "\n")


def read_codex_task_events(task_id: str | None = None) -> list[dict]:
    if not EVENT_LOG_PATH.exists():
        return []

    events: list[dict] = []
    with EVENT_LOG_PATH.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if task_id is None or event.get("task_id") == task_id:
                events.append(event)
    return sorted(events, key=lambda event: str(event.get("created_at", "")), reverse=True)


def ensure_default_customizations() -> None:
    for simulation_name, simulation_dir in SIMULATION_DIRS.items():
        customization_path = simulation_dir / "customization.json"
        if customization_path.exists():
            continue
        _write_customization(customization_path, {"visuals": DEFAULT_VISUALS[simulation_name]})


def reset_lab_runtime_state() -> dict:
    reset_at = datetime.now(timezone.utc).isoformat()
    simulations: dict[str, dict] = {}
    changed_files: list[str] = []
    deleted_files = _delete_implementation_request_artifacts()

    for simulation_name, simulation_dir in SIMULATION_DIRS.items():
        customization_path = simulation_dir / "customization.json"
        _write_customization(customization_path, {"visuals": DEFAULT_VISUALS[simulation_name]})
        result = _run_reset_simulation(simulation_name)
        simulations[simulation_name] = {
            "summary": result.get("summary", {}),
            "parameters": result.get("meta", {}).get("parameters", {}),
        }
        changed_files.extend(
            [
                str(customization_path.relative_to(BASE_DIR)),
                str((simulation_dir / "result.json").relative_to(BASE_DIR)),
            ]
        )

    append_codex_task_event(
        {
            "event_id": uuid4().hex,
            "event_type": "lab_reset",
            "created_at": reset_at,
            "task_id": "",
            "simulation_name": "all",
            "status": "reset",
            "changed_files": changed_files,
            "deleted_files": deleted_files,
        }
    )
    return {
        "reset_at": reset_at,
        "simulations": simulations,
        "changed_files": changed_files,
        "deleted_files": deleted_files,
        "message": "3D-AI Labを初期状態に戻しました。",
    }


def _delete_implementation_request_artifacts() -> list[str]:
    deleted_files: list[str] = []
    targets = [
        EVENT_LOG_PATH,
        IMPLEMENTATION_REQUEST_LOG_PATH,
        WATCHER_STATE_PATH,
        PENDING_IMPLEMENTATION_DIR,
        WATCHER_OUTPUT_DIR,
    ]
    if _watcher_lock_is_stale():
        targets.append(WATCHER_LOCK_PATH)

    for path in targets:
        if not path.exists():
            continue
        deleted_files.append(str(path.relative_to(BASE_DIR)))
        if path.is_dir():
            shutil.rmtree(path)
            path.mkdir(parents=True, exist_ok=True)
        else:
            path.unlink()

    PENDING_IMPLEMENTATION_DIR.mkdir(parents=True, exist_ok=True)
    WATCHER_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return deleted_files


def _watcher_lock_is_stale() -> bool:
    if not WATCHER_LOCK_PATH.exists():
        return False
    try:
        pid = int(WATCHER_LOCK_PATH.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return True
    if pid <= 0:
        return True
    try:
        os.kill(pid, 0)
    except (OSError, ValueError):
        return True
    return False


def _unsupported_plan(task: CodexTaskRecord, *, simulation_name: str, warning: str) -> CodexTaskPlanResponse:
    return CodexTaskPlanResponse(
        task_id=task.task_id,
        status="unsupported",
        simulation_name=simulation_name,
        operations=[],
        affected_files=[],
        warnings=[warning],
        apply_available=False,
    )


def _detect_simulation_name(task: CodexTaskRecord) -> str:
    explicit_name = str(task.simulation_name or task.experiment_spec.get("simulation_name") or "")
    if explicit_name in SIMULATION_DIRS:
        return explicit_name

    candidates = [
        task.source_message,
        task.title,
        str(task.experiment_spec.get("goal") or ""),
        str(task.experiment_spec.get("objects") or ""),
        str(task.experiment_spec.get("parameters") or ""),
    ]
    normalized = unicodedata.normalize("NFKC", " ".join(candidates)).lower()
    if "gravity_ball" in normalized or "ボール" in normalized or "ball" in normalized:
        return "gravity_ball"
    if "maze_agent" in normalized or "迷路" in normalized or "maze" in normalized:
        return "maze_agent"
    if "flocking" in normalized or "群れ" in normalized or "鳥" in normalized or "魚" in normalized or "boids" in normalized:
        return "flocking"
    return str(task.simulation_name or task.experiment_spec.get("simulation_name") or "new_simulation")


def _task_text(task: CodexTaskRecord) -> str:
    parts = [
        task.source_message,
        task.title,
        str(task.experiment_spec.get("goal") or ""),
        str(task.experiment_spec.get("parameters") or ""),
    ]
    return unicodedata.normalize("NFKC", "\n".join(parts)).lower()


def _extract_color(text: str) -> str | None:
    match = HEX_COLOR_PATTERN.search(text)
    if match:
        return match.group(0).lower()

    for name, value in COLOR_NAMES.items():
        if name.lower() in text:
            return value
    return None


def _detect_operations(simulation_name: str, text: str, color: str) -> list[CodexTaskOperation]:
    if simulation_name == "gravity_ball":
        return _gravity_operations(text, color)
    if simulation_name == "maze_agent":
        return _maze_operations(text, color)
    if simulation_name == "flocking":
        return _flocking_operations(text, color)
    return []


def _gravity_operations(text: str, color: str) -> list[CodexTaskOperation]:
    operations: list[CodexTaskOperation] = []
    if _contains_any(text, ["床", "floor", "地面"]):
        operations.append(_operation("floor_color", "床色", color, "floor"))
    if _contains_any(text, ["軌跡", "trajectory", "線"]):
        operations.append(_operation("trajectory_color", "軌跡色", color, "trajectory"))
    if _contains_any(text, ["ボール", "ball", "球"]):
        operations.append(_operation("ball_color", "ボール色", color, "ball"))
    if not operations and _contains_any(text, ["gravity_ball"]):
        operations.append(_operation("ball_color", "ボール色", color, "ball"))
    return operations


def _maze_operations(text: str, color: str) -> list[CodexTaskOperation]:
    operations: list[CodexTaskOperation] = []
    if _contains_any(text, ["壁", "wall"]):
        operations.append(_operation("wall_color", "壁色", color, "wall"))
    if _contains_any(text, ["床", "floor", "タイル"]):
        operations.append(_operation("floor_color", "床色", color, "floor"))
    if _contains_any(text, ["経路", "道", "ルート", "path", "route"]):
        operations.append(_operation("path_color", "経路色", color, "path"))
    if _contains_any(text, ["スタート", "開始", "start"]):
        operations.append(_operation("start_color", "スタート色", color, "start"))
    if _contains_any(text, ["ゴール", "goal"]):
        operations.append(_operation("goal_color", "ゴール色", color, "goal"))
    if _contains_any(text, ["エージェント", "agent color", "agent_color"]):
        operations.append(_operation("agent_color", "エージェント色", color, "agent"))
    return operations


def _flocking_operations(text: str, color: str) -> list[CodexTaskOperation]:
    operations: list[CodexTaskOperation] = []
    if _contains_any(text, ["境界", "枠", "bounds", "boundary"]):
        operations.append(_operation("bounds_color", "境界線色", color, "bounds"))
    if _contains_any(text, ["個体", "群れ", "鳥", "魚", "boid", "boids", "agent", "flocking"]):
        operations.append(CodexTaskOperation(key="agent_palette", label="個体色パレット", value=[color], target="agents"))
    return operations


def _operation(key: str, label: str, value: str, target: str) -> CodexTaskOperation:
    return CodexTaskOperation(key=key, label=label, value=value, target=target)


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword.lower() in text for keyword in keywords)


def _affected_files(simulation_name: str) -> list[str]:
    simulation_dir = SIMULATION_DIRS[simulation_name]
    return [
        str((simulation_dir / "customization.json").relative_to(BASE_DIR)),
        str((simulation_dir / "result.json").relative_to(BASE_DIR)),
        str((simulation_dir / "README.md").relative_to(BASE_DIR)),
    ]


def _read_customization(simulation_name: str, path: Path) -> dict:
    if not path.exists():
        return {"visuals": DEFAULT_VISUALS[simulation_name].copy()}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = {}
    visuals = DEFAULT_VISUALS[simulation_name].copy()
    visuals.update(data.get("visuals") or {})
    data["visuals"] = visuals
    return data


def _write_customization(path: Path, customization: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(customization, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _update_simulation_readme(path: Path, applied_at: str, operations: list[CodexTaskOperation]) -> None:
    start_marker = "<!-- ai-lab-customization:start -->"
    end_marker = "<!-- ai-lab-customization:end -->"
    operation_lines = "\n".join(
        f"- {operation.label}: {_format_operation_value(operation.value)}" for operation in operations
    )
    section = (
        f"{start_marker}\n"
        "## 表示カスタマイズ\n\n"
        "このシミュレーションは、確認付きの限定適用で見た目を調整できます。\n\n"
        f"最終適用: {applied_at}\n\n"
        f"{operation_lines}\n"
        f"{end_marker}\n"
    )
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        text = ""

    if start_marker in text and end_marker in text:
        before = text.split(start_marker, 1)[0].rstrip()
        after = text.split(end_marker, 1)[1].lstrip()
        next_text = f"{before}\n\n{section}"
        if after:
            next_text += f"\n{after}"
    else:
        next_text = f"{text.rstrip()}\n\n{section}" if text.strip() else section

    path.write_text(next_text, encoding="utf-8")


def _format_operation_value(value: str | list[str]) -> str:
    return ", ".join(value) if isinstance(value, list) else value


def _run_simulation(simulation_name: str) -> dict:
    if simulation_name == "gravity_ball":
        config_path = SIMULATION_DIRS[simulation_name] / "config.json"
        return run_gravity_ball_and_save(GravityBallConfig(**_read_config(config_path)))
    if simulation_name == "maze_agent":
        config_path = SIMULATION_DIRS[simulation_name] / "config.json"
        return run_maze_agent_and_save(MazeAgentConfig(**_read_config(config_path)))
    if simulation_name == "flocking":
        config_path = SIMULATION_DIRS[simulation_name] / "config.json"
        return run_flocking_and_save(FlockingConfig(**_read_config(config_path)))
    raise ValueError(f"Unsupported simulation: {simulation_name}")


def _run_reset_simulation(simulation_name: str) -> dict:
    config_path = SIMULATION_DIRS[simulation_name] / "config.json"
    config = _read_config(config_path)
    if simulation_name == "gravity_ball":
        return run_gravity_ball_and_save(GravityBallConfig(**config))
    if simulation_name == "maze_agent":
        return run_maze_agent_and_save(MazeAgentConfig(**config))
    if simulation_name == "flocking":
        if config.get("seed") is None:
            config["seed"] = 123
        return run_flocking_and_save(FlockingConfig(**config))
    raise ValueError(f"Unsupported simulation: {simulation_name}")


def _read_config(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _model_dump(model: CodexTaskOperation) -> dict:
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()
