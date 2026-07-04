from __future__ import annotations

import json
import random
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


AGENT_ID = "agent_1"
RESULT_PATH = Path(__file__).with_name("result.json")
CUSTOMIZATION_PATH = Path(__file__).with_name("customization.json")
DEFAULT_VISUALS = {
    "floor_color": "#1b242d",
    "path_color": "#45c4a0",
    "start_color": "#65d46e",
    "goal_color": "#ffd166",
    "agent_color": "#72a7ff",
    "wall_color": "#000000",
}
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
    randomize: bool = False
    seed: int | None = None
    wall_density: float = 0.32


def run_simulation(config: MazeAgentConfig) -> dict[str, Any]:
    visuals = _load_visuals()
    grid_size, start, goal, walls, seed, maze_type, wall_density = _resolve_layout(config)
    steps_per_cell = _clamp_int(config.steps_per_cell, 1, 60)
    path, visited = _find_path(grid_size, start, goal, walls)
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
                "seed": seed,
                "wall_density": wall_density,
            },
            "visuals": visuals,
        },
        "objects": _build_objects(grid_size, start, goal, walls, path, visuals),
        "frames": frames,
        "summary": {
            "maze_type": maze_type,
            "grid_size": grid_size,
            "start": list(start),
            "goal": list(goal),
            "seed": seed,
            "wall_density": wall_density,
            "wall_count": len(walls),
            "path_length": len(path),
            "visited_count": len(visited),
            "reached_goal": bool(path and path[-1] == goal),
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
    if not result.get("frames") or not result.get("meta", {}).get("visuals"):
        result = run_simulation(MazeAgentConfig())
        write_result(result, path)
    return json.loads(path.read_text(encoding="utf-8"))


def run_and_save(config: MazeAgentConfig, path: Path = RESULT_PATH) -> dict[str, Any]:
    result = run_simulation(config)
    write_result(result, path)
    return result


def _resolve_layout(
    config: MazeAgentConfig,
) -> tuple[int, tuple[int, int], tuple[int, int], set[tuple[int, int]], int | None, str, float]:
    if not config.randomize:
        return 7, START, GOAL, set(WALLS), None, "fixed", 0.0

    grid_size = _normalize_grid_size(config.grid_size)
    start = (0, 0)
    goal = (grid_size - 1, grid_size - 1)
    seed = config.seed if config.seed is not None else random.SystemRandom().randrange(1, 1_000_000)
    wall_density = _clamp_float(config.wall_density, 0.05, 0.55)
    walls = _generate_random_walls(grid_size, start, goal, wall_density, seed)
    return grid_size, start, goal, walls, seed, "random", wall_density


def _generate_random_walls(
    grid_size: int,
    start: tuple[int, int],
    goal: tuple[int, int],
    wall_density: float,
    seed: int,
) -> set[tuple[int, int]]:
    rng = random.Random(seed)
    guaranteed_path = _random_reference_path(grid_size, start, goal, rng)
    candidates = [
        (x, z)
        for x in range(grid_size)
        for z in range(grid_size)
        if (x, z) not in guaranteed_path and (x, z) not in {start, goal}
    ]
    rng.shuffle(candidates)
    wall_count = round(len(candidates) * wall_density)
    return set(candidates[:wall_count])


def _random_reference_path(
    grid_size: int,
    start: tuple[int, int],
    goal: tuple[int, int],
    rng: random.Random,
) -> set[tuple[int, int]]:
    x, z = start
    cells = {start}
    moves = ["x"] * (goal[0] - start[0]) + ["z"] * (goal[1] - start[1])
    rng.shuffle(moves)

    for move in moves:
        if move == "x":
            x = min(x + 1, grid_size - 1)
        else:
            z = min(z + 1, grid_size - 1)
        cells.add((x, z))

    cells.add(goal)
    return cells


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
    visuals: dict[str, str],
) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = [
        {
            "id": "maze_floor",
            "type": "maze_floor",
            "grid_size": grid_size,
            "tile_size": 1,
            "color": visuals["floor_color"],
        },
        {
            "id": "maze_path",
            "type": "path",
            "cells": [list(cell) for cell in path],
            "color": visuals["path_color"],
        },
        {
            "id": "start",
            "type": "marker",
            "cell": list(start),
            "color": visuals["start_color"],
        },
        {
            "id": "goal",
            "type": "marker",
            "cell": list(goal),
            "color": visuals["goal_color"],
        },
        {
            "id": AGENT_ID,
            "type": "agent",
            "radius": 0.22,
            "color": visuals["agent_color"],
        },
    ]

    for index, cell in enumerate(sorted(walls)):
        objects.append(
            {
                "id": f"wall_{index}",
                "type": "wall",
                "cell": list(cell),
                "height": 0.76,
                "color": visuals["wall_color"],
            }
        )

    return objects


def _world_position(cell: tuple[int, int], grid_size: int) -> list[float]:
    x, z = cell
    offset = (grid_size - 1) / 2
    return [round(x - offset, 4), 0.0, round(z - offset, 4)]


def _clamp_int(value: int, minimum: int, maximum: int) -> int:
    return min(max(int(value), minimum), maximum)


def _clamp_float(value: float, minimum: float, maximum: float) -> float:
    return min(max(float(value), minimum), maximum)


def _normalize_grid_size(value: int) -> int:
    grid_size = _clamp_int(value, 5, 11)
    if grid_size % 2 == 0:
        grid_size += 1 if grid_size < 11 else -1
    return grid_size


def _load_visuals(path: Path = CUSTOMIZATION_PATH) -> dict[str, str]:
    visuals = DEFAULT_VISUALS.copy()
    if not path.exists():
        return visuals
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return visuals
    for key, value in (data.get("visuals") or {}).items():
        if key in visuals and isinstance(value, str):
            visuals[key] = value
    return visuals


if __name__ == "__main__":
    write_result(run_simulation(MazeAgentConfig()))
