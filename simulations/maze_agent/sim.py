from __future__ import annotations

import json
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


AGENT_ID = "agent_1"
RESULT_PATH = Path(__file__).with_name("result.json")
START = (0, 0)
GOAL = (6, 6)
WALLS = {
    (1, 0),
    (1, 1),
    (1, 3),
    (2, 3),
    (3, 3),
    (4, 1),
    (4, 2),
    (4, 3),
    (5, 5),
    (3, 5),
    (2, 5),
}


@dataclass(frozen=True)
class MazeAgentConfig:
    grid_size: int = 7
    steps_per_cell: int = 12
    dt: float = 0.08
    show_search: bool = False


def run_simulation(config: MazeAgentConfig) -> dict[str, Any]:
    grid_size = _clamp_int(config.grid_size, 5, 11)
    if grid_size != 7:
        grid_size = 7

    steps_per_cell = _clamp_int(config.steps_per_cell, 1, 60)
    path, visited = _find_path(grid_size, START, GOAL, WALLS)
    frames = _build_frames(path, steps_per_cell, config.dt, grid_size)

    return {
        "meta": {
            "simulation_name": "maze_agent",
            "steps": len(frames),
            "dt": config.dt,
            "parameters": {
                **asdict(config),
                "grid_size": grid_size,
                "steps_per_cell": steps_per_cell,
            },
        },
        "objects": _build_objects(grid_size, START, GOAL, WALLS, path),
        "frames": frames,
        "summary": {
            "grid_size": grid_size,
            "start": list(START),
            "goal": list(GOAL),
            "path_length": len(path),
            "visited_count": len(visited),
            "reached_goal": bool(path and path[-1] == GOAL),
            "duration": round(len(frames) * config.dt, 4),
        },
    }


def write_result(result: dict[str, Any], path: Path = RESULT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


def load_result(path: Path = RESULT_PATH) -> dict[str, Any]:
    if not path.exists():
        result = run_simulation(MazeAgentConfig())
        write_result(result, path)
        return result

    result = json.loads(path.read_text(encoding="utf-8"))
    if not result.get("frames"):
        result = run_simulation(MazeAgentConfig())
        write_result(result, path)
    return json.loads(path.read_text(encoding="utf-8"))


def run_and_save(config: MazeAgentConfig, path: Path = RESULT_PATH) -> dict[str, Any]:
    result = run_simulation(config)
    write_result(result, path)
    return result


def _find_path(
    grid_size: int,
    start: tuple[int, int],
    goal: tuple[int, int],
    walls: set[tuple[int, int]],
) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    queue: deque[tuple[int, int]] = deque([start])
    previous: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    visited: list[tuple[int, int]] = []

    while queue:
        cell = queue.popleft()
        visited.append(cell)
        if cell == goal:
            break

        for neighbor in _neighbors(cell, grid_size):
            if neighbor in walls or neighbor in previous:
                continue
            previous[neighbor] = cell
            queue.append(neighbor)

    if goal not in previous:
        return [start], visited

    path: list[tuple[int, int]] = []
    cursor: tuple[int, int] | None = goal
    while cursor is not None:
        path.append(cursor)
        cursor = previous[cursor]
    path.reverse()
    return path, visited


def _neighbors(cell: tuple[int, int], grid_size: int) -> list[tuple[int, int]]:
    x, z = cell
    candidates = [(x + 1, z), (x, z + 1), (x - 1, z), (x, z - 1)]
    return [(nx, nz) for nx, nz in candidates if 0 <= nx < grid_size and 0 <= nz < grid_size]


def _build_frames(
    path: list[tuple[int, int]],
    steps_per_cell: int,
    dt: float,
    grid_size: int,
) -> list[dict[str, Any]]:
    if not path:
        return []

    frames: list[dict[str, Any]] = []
    frame_index = 0
    for current, nxt in zip(path, path[1:]):
        current_pos = _world_position(current, grid_size)
        next_pos = _world_position(nxt, grid_size)
        for step in range(steps_per_cell):
            alpha = step / steps_per_cell
            position = [
                round(current_pos[0] + (next_pos[0] - current_pos[0]) * alpha, 4),
                0.28,
                round(current_pos[2] + (next_pos[2] - current_pos[2]) * alpha, 4),
            ]
            frames.append(_frame(frame_index, dt, position, current, nxt))
            frame_index += 1

    final_pos = _world_position(path[-1], grid_size)
    frames.append(_frame(frame_index, dt, [final_pos[0], 0.28, final_pos[2]], path[-1], path[-1]))
    return frames


def _frame(
    frame_index: int,
    dt: float,
    position: list[float],
    cell: tuple[int, int],
    target_cell: tuple[int, int],
) -> dict[str, Any]:
    return {
        "t": frame_index,
        "time": round(frame_index * dt, 4),
        "objects": {
            AGENT_ID: {
                "position": position,
                "cell": list(cell),
                "target_cell": list(target_cell),
            }
        },
    }


def _build_objects(
    grid_size: int,
    start: tuple[int, int],
    goal: tuple[int, int],
    walls: set[tuple[int, int]],
    path: list[tuple[int, int]],
) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = [
        {
            "id": "maze_floor",
            "type": "maze_floor",
            "grid_size": grid_size,
            "tile_size": 1,
            "color": "#1b242d",
        },
        {
            "id": "maze_path",
            "type": "path",
            "cells": [list(cell) for cell in path],
            "color": "#45c4a0",
        },
        {
            "id": "start",
            "type": "marker",
            "cell": list(start),
            "color": "#65d46e",
        },
        {
            "id": "goal",
            "type": "marker",
            "cell": list(goal),
            "color": "#ffd166",
        },
        {
            "id": AGENT_ID,
            "type": "agent",
            "radius": 0.22,
            "color": "#72a7ff",
        },
    ]

    for index, cell in enumerate(sorted(walls)):
        objects.append(
            {
                "id": f"wall_{index}",
                "type": "wall",
                "cell": list(cell),
                "height": 0.76,
                "color": "#566273",
            }
        )

    return objects


def _world_position(cell: tuple[int, int], grid_size: int) -> list[float]:
    x, z = cell
    offset = (grid_size - 1) / 2
    return [round(x - offset, 4), 0.0, round(z - offset, 4)]


def _clamp_int(value: int, minimum: int, maximum: int) -> int:
    return min(max(int(value), minimum), maximum)


if __name__ == "__main__":
    write_result(run_simulation(MazeAgentConfig()))
