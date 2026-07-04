from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


BALL_ID = "ball_1"
BALL_RADIUS = 0.3
RESULT_PATH = Path(__file__).with_name("result.json")


@dataclass(frozen=True)
class GravityBallConfig:
    gravity: float = 9.8
    initial_height: float = 5.0
    bounce: float = 0.72
    steps: int = 360
    dt: float = 0.016


def run_simulation(config: GravityBallConfig) -> dict[str, Any]:
    y = max(config.initial_height, BALL_RADIUS)
    velocity = 0.0
    bounces = 0
    max_height = y
    min_height = y
    frames: list[dict[str, Any]] = []

    for step in range(config.steps):
        time = round(step * config.dt, 4)
        frames.append(
            {
                "t": step,
                "time": time,
                "objects": {
                    BALL_ID: {
                        "position": [0.0, round(y, 4), 0.0],
                        "velocity": [0.0, round(velocity, 4), 0.0],
                    }
                },
            }
        )

        velocity -= config.gravity * config.dt
        y += velocity * config.dt

        if y <= BALL_RADIUS:
            y = BALL_RADIUS
            if abs(velocity) > 0.08:
                bounces += 1
            velocity = -velocity * config.bounce
            if abs(velocity) < 0.05:
                velocity = 0.0

        max_height = max(max_height, y)
        min_height = min(min_height, y)

    return {
        "meta": {
            "simulation_name": "gravity_ball",
            "steps": config.steps,
            "dt": config.dt,
            "parameters": asdict(config),
        },
        "objects": [
            {
                "id": BALL_ID,
                "type": "sphere",
                "radius": BALL_RADIUS,
                "color": "#ffd166",
            },
            {
                "id": "floor",
                "type": "plane",
                "size": [10, 10],
                "color": "#1a222b",
            },
        ],
        "frames": frames,
        "summary": {
            "bounces": bounces,
            "max_height": round(max_height, 4),
            "min_height": round(min_height, 4),
            "duration": round(config.steps * config.dt, 4),
        },
    }


def write_result(result: dict[str, Any], path: Path = RESULT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


def load_result(path: Path = RESULT_PATH) -> dict[str, Any]:
    if not path.exists():
        result = run_simulation(GravityBallConfig())
        write_result(result, path)
        return result

    result = json.loads(path.read_text(encoding="utf-8"))
    if not result.get("frames"):
        result = run_simulation(GravityBallConfig())
        write_result(result, path)
    return json.loads(path.read_text(encoding="utf-8"))


def run_and_save(config: GravityBallConfig, path: Path = RESULT_PATH) -> dict[str, Any]:
    result = run_simulation(config)
    write_result(result, path)
    return result


if __name__ == "__main__":
    write_result(run_simulation(GravityBallConfig()))
