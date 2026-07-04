from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from .codex_task_builder import build_codex_task


@dataclass(frozen=True)
class LabAssistantResponse:
    reply: str
    experiment_spec: dict[str, Any]
    codex_task: str
    assistant_notes: list[str]
    suggested_action: str | None = None
    simulation_params: dict[str, float | int | bool] | None = None


def generate_lab_assistant_response(message: str, session_id: str) -> LabAssistantResponse:
    cleaned = message.strip()
    if not cleaned:
        spec = _default_experiment_spec()
        return LabAssistantResponse(
            reply="まずは試したいことを一文で入力してみましょう。",
            experiment_spec=spec,
            codex_task=build_codex_task(spec),
            assistant_notes=["入力が空だったため、最小の実験案を返しました。"],
        )

    normalized = unicodedata.normalize("NFKC", cleaned).lower()
    if _looks_like_gravity_ball(normalized):
        params = _extract_gravity_ball_params(normalized)
        spec = _gravity_ball_spec(cleaned, params)
        reply = _gravity_ball_reply(cleaned, params)
        return LabAssistantResponse(
            reply=reply,
            experiment_spec=spec,
            codex_task=build_codex_task(spec),
            assistant_notes=[
                "Phase 3のAPIキーなし版として、ルールベースで実験仕様に分解しました。",
                "gravity_ball はPhase 4〜5で実装済みのため、実行可能なアクションも返します。",
            ],
            suggested_action="run_gravity_ball",
            simulation_params=params or None,
        )

    if any(keyword in normalized for keyword in ["群れ", "鳥", "魚", "flocking", "boids", "boid"]):
        params = _extract_flocking_params(normalized)
        spec = _flocking_spec(cleaned, params)
        return LabAssistantResponse(
            reply="flocking の実験案に分解しました。複数エージェントが近くの仲間に合わせて群れ行動する様子を実行して表示します。",
            experiment_spec=spec,
            codex_task=build_codex_task(spec),
            assistant_notes=[
                "flocking はPhase 7bとして実行可能です。",
                "強化学習ではなく、Boids風のルールベースシミュレーションとして実行します。",
            ],
            suggested_action="run_flocking",
            simulation_params=params,
        )

    if any(keyword in normalized for keyword in ["迷路", "maze", "エージェント", "agent", "学習", "強化学習"]):
        spec = _maze_agent_spec(cleaned)
        wants_learning = any(keyword in normalized for keyword in ["学習", "強化学習", "rl", "reinforcement"])
        wants_random = any(keyword in normalized for keyword in ["ランダム", "random", "毎回", "生成"])
        return LabAssistantResponse(
            reply=(
                "迷路エージェントの実験案に分解しました。"
                "Phase 7aでは強化学習ではなく軽量探索で、スタートからゴールへ進む様子を実行して表示します。"
            ),
            experiment_spec=spec,
            codex_task=build_codex_task(spec),
            assistant_notes=[
                "maze_agent はPhase 7aとして実行可能です。",
                "強化学習は後続フェーズで扱い、今回は固定迷路のBFS系探索として実行します。"
                if wants_learning
                else "今回は固定迷路のBFS系探索として実行します。",
            ],
            suggested_action="run_maze_agent",
            simulation_params={
                "grid_size": 9 if wants_random else 7,
                "steps_per_cell": 12,
                "dt": 0.08,
                "show_search": False,
                "randomize": wants_random,
                "wall_density": 0.32,
            },
        )

    spec = _generic_experiment_spec(cleaned)
    return LabAssistantResponse(
        reply=(
            "実験案として整理しました。"
            "まずは登場物、動き、変更できる値、観察したい結果を1つずつ決めると、3Dシミュレーションにしやすくなります。"
        ),
        experiment_spec=spec,
        codex_task=build_codex_task(spec),
        assistant_notes=[
            "未対応の題材のため、今は実行せずCodex向けタスク案として返します。",
            "Phase 6以降で、このタスク案を実装依頼に使えます。",
        ],
    )


def generate_reply(message: str, session_id: str) -> str:
    """Compatibility wrapper for older callers."""
    return generate_lab_assistant_response(message, session_id).reply


def _looks_like_gravity_ball(message: str) -> bool:
    return any(
        keyword in message
        for keyword in ["重力", "gravity", "落下", "ボール", "ball", "跳ね", "高さ", "height", "反発", "bounce"]
    )


def _extract_gravity_ball_params(message: str) -> dict[str, float | int | bool]:
    params: dict[str, float | int | bool] = {}
    gravity_value = _extract_number_after_keywords(message, ["重力", "gravity"])
    height_value = _extract_number_after_keywords(message, ["高さ", "height", "初期高さ"])
    bounce_value = _extract_number_after_keywords(message, ["反発係数", "反発", "bounce"])

    if gravity_value is not None:
        params["gravity"] = _clamp(gravity_value, 0.1, 50.0)
    if height_value is not None:
        params["initial_height"] = _clamp(height_value, 0.6, 12.0)
    if bounce_value is not None:
        params["bounce"] = _clamp(bounce_value, 0.0, 0.98)

    if any(keyword in message for keyword in ["強", "大き", "速", "早"]):
        params.setdefault("gravity", 16.0)
    if any(keyword in message for keyword in ["弱", "小さ", "ゆっくり", "遅"]):
        params.setdefault("gravity", 4.5)
    if any(keyword in message for keyword in ["高", "上"]):
        params.setdefault("initial_height", 8.0)
    if any(keyword in message for keyword in ["低", "下"]):
        params.setdefault("initial_height", 3.0)
    if any(keyword in message for keyword in ["よく跳", "弾", "反発"]):
        params.setdefault("bounce", 0.88)
    if any(keyword in message for keyword in ["跳ねない", "反発しない"]):
        params.setdefault("bounce", 0.2)

    return params


def _extract_flocking_params(message: str) -> dict[str, float | int | bool]:
    params: dict[str, float | int | bool] = {
        "agent_count": 30,
        "steps": 360,
        "dt": 0.08,
        "cohesion_weight": 0.55,
        "alignment_weight": 0.65,
        "separation_weight": 1.25,
        "perception_radius": 2.2,
        "separation_radius": 0.7,
        "bounds": 6.0,
    }
    count = _extract_number_after_keywords(message, ["個体", "数", "agent", "boid"])
    if count is not None:
        params["agent_count"] = int(_clamp(count, 10, 80))
    if any(keyword in message for keyword in ["たくさん", "多く", "増や"]):
        params["agent_count"] = 50
    if any(keyword in message for keyword in ["少な", "小さ"]):
        params["agent_count"] = 15
    if any(keyword in message for keyword in ["まとま", "集ま", "密"]):
        params["cohesion_weight"] = 0.9
    if any(keyword in message for keyword in ["ばら", "散ら"]):
        params["separation_weight"] = 1.8
    return params


def _gravity_ball_reply(message: str, params: dict[str, float | int | bool]) -> str:
    if params:
        changes = "、".join(f"{_parameter_label(key)}={value}" for key, value in params.items())
        return f"gravity_ball の実験案に分解しました。今回は {changes} として、落下と反発の変化を観察します。"
    return "gravity_ball の実験案に分解しました。重力、初期高さ、反発係数を変えると、落下の速さや跳ね返り方を比べられます。"


def _gravity_ball_spec(message: str, params: dict[str, float | int | bool]) -> dict[str, Any]:
    return {
        "title": "重力ボール実験",
        "simulation_name": "gravity_ball",
        "goal": "重力、初期高さ、反発係数を変えたときのボールの落下と跳ね返りを観察する",
        "source_message": message,
        "objects": ["ボール", "床", "軌跡"],
        "parameters": {
            "gravity": params.get("gravity", "変更可能"),
            "initial_height": params.get("initial_height", "変更可能"),
            "bounce": params.get("bounce", "変更可能"),
        },
        "observations": ["落下速度", "跳ね返り回数", "最高到達点", "静止に近づく様子"],
        "phase": "Phase 4-5 実行可能",
    }


def _maze_agent_spec(message: str) -> dict[str, Any]:
    return {
        "title": "迷路エージェント実験",
        "simulation_name": "maze_agent",
        "goal": "エージェントが固定迷路の壁を避けながらスタートからゴールへ進む様子を観察する",
        "source_message": message,
        "objects": ["迷路の床", "壁", "エージェント", "スタート", "ゴール"],
        "parameters": {
            "grid_size": "7x7、9x9、11x11",
            "steps_per_cell": "1マス移動あたりの表示フレーム数",
            "randomize": "ランダム迷路を生成するか",
            "seed": "同じ迷路を再現するための番号",
            "wall_density": "壁の多さ",
            "show_search": "探索過程表示の候補",
        },
        "observations": ["壁を避ける経路", "ゴール到達までのステップ数", "最終フレームの到達位置"],
        "phase": "Phase 7a 実行可能",
    }


def _flocking_spec(message: str, params: dict[str, float | int | bool]) -> dict[str, Any]:
    return {
        "title": "群れ行動実験",
        "simulation_name": "flocking",
        "goal": "複数エージェントが近くの仲間へ寄り、向きを合わせ、近すぎる相手から離れることで群れを作る様子を観察する",
        "source_message": message,
        "objects": ["群れエージェント", "移動範囲", "進行方向"],
        "parameters": {
            "agent_count": params.get("agent_count", 30),
            "cohesion_weight": params.get("cohesion_weight", 0.55),
            "alignment_weight": params.get("alignment_weight", 0.65),
            "separation_weight": params.get("separation_weight", 1.25),
            "seed": "任意",
        },
        "observations": ["群れのまとまり", "個体間距離", "進行方向の揃い方", "パラメータ変更による軌道の違い"],
        "phase": "Phase 7b 実行可能",
    }


def _generic_experiment_spec(message: str) -> dict[str, Any]:
    return {
        "title": "新しい3D実験案",
        "simulation_name": "new_simulation",
        "goal": f"学生の入力「{message}」を、小さく動く3Dシミュレーションとして試す",
        "source_message": message,
        "objects": ["主役になる物体", "環境", "ゴールまたは観察対象"],
        "parameters": {
            "speed": "動きの速さ",
            "count": "物体の数",
            "duration": "観察時間",
        },
        "observations": ["何が変化したか", "どのパラメータが結果に効いたか", "次に変えたい条件"],
        "phase": "Phase 6以降の実装候補",
    }


def _default_experiment_spec() -> dict[str, Any]:
    return {
        "title": "最小実験案",
        "simulation_name": "gravity_ball",
        "goal": "重力で落ちるボールを観察する",
        "objects": ["ボール", "床"],
        "parameters": {"gravity": "変更可能", "initial_height": "変更可能", "bounce": "変更可能"},
        "observations": ["落下速度", "跳ね返り"],
        "phase": "Phase 4-5 実行可能",
    }


def _extract_number_after_keywords(message: str, keywords: list[str]) -> float | None:
    number_pattern = r"([-+]?\d+(?:\.\d+)?)"
    for keyword in keywords:
        match = re.search(rf"{re.escape(keyword)}[^\d+\-.]*{number_pattern}", message)
        if match:
            return float(match.group(1))
    return None


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return min(max(value, minimum), maximum)


def _parameter_label(key: str) -> str:
    return {
        "gravity": "重力",
        "initial_height": "初期高さ",
        "bounce": "反発係数",
    }.get(key, key)
