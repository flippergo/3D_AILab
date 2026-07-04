from __future__ import annotations

import json
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


RESULT_PATH = Path(__file__).with_name("result.json")
CUSTOMIZATION_PATH = Path(__file__).with_name("customization.json")
MIN_SPEED = 0.45
MAX_SPEED = 1.85
DEFAULT_VISUALS = {
    "agent_palette": ["#8fd3ff", "#ffd166", "#45c4a0"],
    "bounds_color": "#45c4a0",
}


@dataclass(frozen=True)
class FlockingConfig:
    agent_count: int = 30
    steps: int = 360
    dt: float = 0.08
    seed: int | None = None
    cohesion_weight: float = 0.55
    alignment_weight: float = 0.65
    separation_weight: float = 1.25
    perception_radius: float = 2.2
    separation_radius: float = 0.7
    bounds: float = 6.0


def run_simulation(config: FlockingConfig) -> dict[str, Any]:
    visuals = _load_visuals()
    agent_count = _clamp_int(config.agent_count, 10, 80)
    steps = _clamp_int(config.steps, 120, 900)
    dt = _clamp_float(config.dt, 0.02, 0.2)
    seed = config.seed if config.seed is not None else random.SystemRandom().randrange(1, 1_000_000)
    rng = random.Random(seed)

    bounds = _clamp_float(config.bounds, 3.0, 12.0)
    cohesion_weight = _clamp_float(config.cohesion_weight, 0.0, 2.0)
    alignment_weight = _clamp_float(config.alignment_weight, 0.0, 2.0)
    separation_weight = _clamp_float(config.separation_weight, 0.0, 3.0)
    perception_radius = _clamp_float(config.perception_radius, 0.6, 5.0)
    separation_radius = _clamp_float(config.separation_radius, 0.2, 2.0)

    positions = [_random_position(rng, bounds) for _ in range(agent_count)]
    velocities = [_random_velocity(rng) for _ in range(agent_count)]
    frames: list[dict[str, Any]] = []
    spread_total = 0.0
    speed_total = 0.0

    for step in range(steps):
        frames.append(_build_frame(step, dt, positions, velocities))
        spread_total += _average_distance_from_center(positions)
        speed_total += sum(_length(velocity) for velocity in velocities) / agent_count
        positions, velocities = _advance(
            positions=positions,
            velocities=velocities,
            dt=dt,
            bounds=bounds,
            cohesion_weight=cohesion_weight,
            alignment_weight=alignment_weight,
            separation_weight=separation_weight,
            perception_radius=perception_radius,
            separation_radius=separation_radius,
        )

    parameters = {
        **asdict(config),
        "agent_count": agent_count,
        "steps": steps,
        "dt": dt,
        "seed": seed,
        "cohesion_weight": cohesion_weight,
        "alignment_weight": alignment_weight,
        "separation_weight": separation_weight,
        "perception_radius": perception_radius,
        "separation_radius": separation_radius,
        "bounds": bounds,
    }
    return {
        "meta": {
            "simulation_name": "flocking",
            "steps": steps,
            "dt": dt,
            "parameters": parameters,
            "visuals": visuals,
        },
        "objects": [
            {
                "id": f"boid_{index}",
                "type": "boid",
                "radius": 0.14,
                "color": _agent_color(index, agent_count, visuals["agent_palette"]),
            }
            for index in range(agent_count)
        ],
        "frames": frames,
        "summary": {
            "agent_count": agent_count,
            "seed": seed,
            "duration": round(steps * dt, 4),
            "bounds": bounds,
            "avg_speed": round(speed_total / steps, 4),
            "avg_spread": round(spread_total / steps, 4),
        },
    }


def write_result(result: dict[str, Any], path: Path = RESULT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


def load_result(path: Path = RESULT_PATH) -> dict[str, Any]:
    if not path.exists():
        result = run_simulation(FlockingConfig())
        write_result(result, path)
        return result

    result = json.loads(path.read_text(encoding="utf-8"))
    if not result.get("frames") or not result.get("meta", {}).get("visuals"):
        result = run_simulation(FlockingConfig())
        write_result(result, path)
    return json.loads(path.read_text(encoding="utf-8"))


def run_and_save(config: FlockingConfig, path: Path = RESULT_PATH) -> dict[str, Any]:
    result = run_simulation(config)
    write_result(result, path)
    return result


def _advance(
    *,
    positions: list[list[float]],
    velocities: list[list[float]],
    dt: float,
    bounds: float,
    cohesion_weight: float,
    alignment_weight: float,
    separation_weight: float,
    perception_radius: float,
    separation_radius: float,
) -> tuple[list[list[float]], list[list[float]]]:
    next_positions: list[list[float]] = []
    next_velocities: list[list[float]] = []

    for index, position in enumerate(positions):
        neighbors: list[int] = []
        close_neighbors: list[int] = []
        for other_index, other_position in enumerate(positions):
            if other_index == index:
                continue
            distance = _distance(position, other_position)
            if distance <= perception_radius:
                neighbors.append(other_index)
            if distance <= separation_radius:
                close_neighbors.append(other_index)

        acceleration = [0.0, 0.0, 0.0]
        if neighbors:
            center = _average([positions[neighbor] for neighbor in neighbors])
            average_velocity = _average([velocities[neighbor] for neighbor in neighbors])
            acceleration = _add(acceleration, _scale(_subtract(center, position), cohesion_weight * 0.12))
            acceleration = _add(acceleration, _scale(_subtract(average_velocity, velocities[index]), alignment_weight * 0.18))

        if close_neighbors:
            separation = [0.0, 0.0, 0.0]
            for neighbor in close_neighbors:
                away = _subtract(position, positions[neighbor])
                distance = max(_length(away), 0.001)
                separation = _add(separation, _scale(away, 1.0 / (distance * distance)))
            acceleration = _add(acceleration, _scale(separation, separation_weight * 0.22))

        acceleration = _add(acceleration, _bounds_force(position, bounds))
        velocity = _limit_speed(_add(velocities[index], _scale(acceleration, dt)), MIN_SPEED, MAX_SPEED)
        next_position = _add(position, _scale(velocity, dt))
        next_positions.append(next_position)
        next_velocities.append(velocity)

    return next_positions, next_velocities


def _build_frame(step: int, dt: float, positions: list[list[float]], velocities: list[list[float]]) -> dict[str, Any]:
    return {
        "t": step,
        "time": round(step * dt, 4),
        "objects": {
            f"boid_{index}": {
                "position": [round(value, 4) for value in position],
                "velocity": [round(value, 4) for value in velocities[index]],
            }
            for index, position in enumerate(positions)
        },
    }


def _random_position(rng: random.Random, bounds: float) -> list[float]:
    return [
        rng.uniform(-bounds * 0.55, bounds * 0.55),
        rng.uniform(0.45, bounds * 0.45),
        rng.uniform(-bounds * 0.55, bounds * 0.55),
    ]


def _random_velocity(rng: random.Random) -> list[float]:
    angle = rng.uniform(0, math.tau)
    pitch = rng.uniform(-0.18, 0.18)
    speed = rng.uniform(0.8, 1.4)
    return [math.cos(angle) * speed, pitch * speed, math.sin(angle) * speed]


def _bounds_force(position: list[float], bounds: float) -> list[float]:
    force = [0.0, 0.0, 0.0]
    limit = bounds
    floor = 0.25
    ceiling = bounds * 0.75
    for axis in (0, 2):
        if position[axis] < -limit:
            force[axis] += 1.2
        elif position[axis] > limit:
            force[axis] -= 1.2
    if position[1] < floor:
        force[1] += 1.1
    elif position[1] > ceiling:
        force[1] -= 1.1
    return force


def _average_distance_from_center(positions: list[list[float]]) -> float:
    center = _average(positions)
    return sum(_distance(position, center) for position in positions) / len(positions)


def _agent_color(index: int, total: int, palette: list[str]) -> str:
    if palette:
        return palette[index % len(palette)]
    hue = index / max(total, 1)
    r, g, b = _hsv_to_rgb(hue, 0.58, 1.0)
    return f"#{r:02x}{g:02x}{b:02x}"


def _hsv_to_rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    i = int(h * 6)
    f = h * 6 - i
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    r, g, b = [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)][i % 6]
    return int(r * 255), int(g * 255), int(b * 255)


def _average(vectors: list[list[float]]) -> list[float]:
    return [sum(vector[axis] for vector in vectors) / len(vectors) for axis in range(3)]


def _add(a: list[float], b: list[float]) -> list[float]:
    return [a[axis] + b[axis] for axis in range(3)]


def _subtract(a: list[float], b: list[float]) -> list[float]:
    return [a[axis] - b[axis] for axis in range(3)]


def _scale(vector: list[float], factor: float) -> list[float]:
    return [value * factor for value in vector]


def _distance(a: list[float], b: list[float]) -> float:
    return _length(_subtract(a, b))


def _length(vector: list[float]) -> float:
    return math.sqrt(sum(value * value for value in vector))


def _limit_speed(vector: list[float], minimum: float, maximum: float) -> list[float]:
    length = _length(vector)
    if length < 0.001:
        return [minimum, 0.0, 0.0]
    if length < minimum:
        return _scale(vector, minimum / length)
    if length > maximum:
        return _scale(vector, maximum / length)
    return vector


def _clamp_int(value: int, minimum: int, maximum: int) -> int:
    return min(max(int(value), minimum), maximum)


def _clamp_float(value: float, minimum: float, maximum: float) -> float:
    return min(max(float(value), minimum), maximum)


def _load_visuals(path: Path = CUSTOMIZATION_PATH) -> dict[str, Any]:
    visuals = {
        "agent_palette": list(DEFAULT_VISUALS["agent_palette"]),
        "bounds_color": DEFAULT_VISUALS["bounds_color"],
    }
    if not path.exists():
        return visuals
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return visuals
    custom_visuals = data.get("visuals") or {}
    palette = custom_visuals.get("agent_palette")
    if isinstance(palette, list) and all(isinstance(value, str) for value in palette):
        visuals["agent_palette"] = palette
    bounds_color = custom_visuals.get("bounds_color")
    if isinstance(bounds_color, str):
        visuals["bounds_color"] = bounds_color
    return visuals


if __name__ == "__main__":
    write_result(run_simulation(FlockingConfig()))
