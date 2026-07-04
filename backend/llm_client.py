from __future__ import annotations

import json
import os
import re
import unicodedata
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from .codex_task_builder import build_codex_task

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional fallback before dependencies are installed
    load_dotenv = None

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional fallback before dependencies are installed
    OpenAI = None

BASE_DIR = Path(__file__).resolve().parent.parent
SESSION_LOG_DIR = BASE_DIR / "logs" / "sessions"
SESSION_ID_PATTERN = re.compile(r"[^a-zA-Z0-9_-]")
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"

if load_dotenv is not None:
    load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class LabAssistantResponse:
    reply: str
    experiment_spec: dict[str, Any]
    codex_task: str | None
    assistant_notes: list[str]
    suggested_action: str | None = None
    simulation_params: dict[str, float | int | bool] | None = None


def generate_lab_assistant_response(message: str, session_id: str) -> LabAssistantResponse:
    rule_response = _generate_rule_based_response(message=message, session_id=session_id)
    if not _openai_enabled():
        return rule_response

    openai_reply = _generate_openai_reply(
        message=message,
        session_id=session_id,
        rule_response=rule_response,
    )
    if not openai_reply:
        return replace(
            rule_response,
            assistant_notes=[
                *rule_response.assistant_notes,
                "OpenAI APIを呼び出せなかったため、ルールベース応答にフォールバックしました。",
            ],
        )

    return replace(
        rule_response,
        reply=openai_reply,
        assistant_notes=[
            "OpenAI APIで自然文の返答を生成しました。",
            *rule_response.assistant_notes,
        ],
    )


def _generate_rule_based_response(message: str, session_id: str) -> LabAssistantResponse:
    cleaned = message.strip()
    if not cleaned:
        spec = _default_experiment_spec()
        return LabAssistantResponse(
            reply="まずは試したいことを一文で入力してみましょう。",
            experiment_spec=spec,
            codex_task=None,
            assistant_notes=["入力が空だったため、最小の実験案を返しました。"],
        )

    normalized = unicodedata.normalize("NFKC", cleaned).lower()
    if _looks_like_general_lab_question(normalized):
        spec = _default_experiment_spec()
        return LabAssistantResponse(
            reply=(
                "今は gravity_ball, maze_agent, flocking を試せます。"
                "重力や高さを変える、迷路をランダム生成する、群れの個体数やまとまりを変える、といった指示をチャットから送れます。"
            ),
            experiment_spec=spec,
            codex_task=None,
            assistant_notes=["一般的な使い方案内として返しました。"],
        )

    if _looks_like_existing_simulation_change(normalized):
        spec = _existing_simulation_change_spec(cleaned, normalized)
        return LabAssistantResponse(
            reply=(
                "既存シミュレーションの変更案として整理しました。"
                "Phase 6aでは自動実装せず、Codex依頼案を確認・保存・コピーできる形で用意します。"
            ),
            experiment_spec=spec,
            codex_task=build_codex_task(spec),
            assistant_notes=[
                "Phase 6aではCodex依頼案を作るだけで、ソースコードの変更は行いません。",
                "実装する場合は、人間が内容を確認してからCodexに渡します。",
            ],
        )

    if _looks_like_gravity_ball(normalized):
        params = _extract_gravity_ball_params(normalized)
        spec = _gravity_ball_spec(cleaned, params)
        reply = _gravity_ball_reply(cleaned, params)
        return LabAssistantResponse(
            reply=reply,
            experiment_spec=spec,
            codex_task=build_codex_task(spec),
            assistant_notes=[
                "ルールベースで実行条件を抽出しました。",
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
            "実験案として整理しました。Phase 6aではまだ実行せず、Codex依頼案として確認できるようにします。"
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


def _openai_enabled() -> bool:
    enabled = os.getenv("OPENAI_ENABLED", "false").strip().lower()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    return enabled in {"1", "true", "yes", "on"} and bool(api_key) and OpenAI is not None


def _generate_openai_reply(
    *,
    message: str,
    session_id: str,
    rule_response: LabAssistantResponse,
) -> str | None:
    model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip() or DEFAULT_OPENAI_MODEL
    timeout = _read_timeout_seconds()
    try:
        client = OpenAI(timeout=timeout)
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": _openai_system_prompt(),
                },
                {
                    "role": "user",
                    "content": _build_openai_user_context(
                        message=message,
                        session_id=session_id,
                        rule_response=rule_response,
                    ),
                },
            ],
        )
        return _extract_response_text(response)
    except Exception:
        return None


def _read_timeout_seconds() -> float:
    value = os.getenv("OPENAI_TIMEOUT_SECONDS", "20").strip()
    try:
        return max(3.0, min(float(value), 60.0))
    except ValueError:
        return 20.0


def _openai_system_prompt() -> str:
    return """あなたは3D-AI Labのラボ助手です。
学生に一方的に講義する先生ではなく、学生の「試したいこと」を小さな3D実験に分解して一緒に考える助手として振る舞ってください。

重要な制約:
- 返答は日本語で、初心者向けに短く具体的にしてください。
- 実行可能な既存シミュレーションは gravity_ball, maze_agent, flocking です。
- Phase 6aではCodex依頼案を作成・保存・コピーできるだけで、自動実装やソースコード変更は行いません。
- APIキー、内部実装、環境変数の値は説明しないでください。
- 返答は自然文だけにしてください。JSONやMarkdown表は不要です。
- 既存の構造化判定結果に反するアクションを約束しないでください。
"""


def _build_openai_user_context(
    *,
    message: str,
    session_id: str,
    rule_response: LabAssistantResponse,
) -> str:
    context = {
        "student_message": message,
        "recent_conversation": _load_recent_session_context(session_id),
        "structured_interpretation": {
            "suggested_action": rule_response.suggested_action,
            "simulation_params": rule_response.simulation_params,
            "experiment_spec": rule_response.experiment_spec,
            "assistant_notes": rule_response.assistant_notes,
        },
        "reply_goal": (
            "上の構造化判定を踏まえて、学生に次の一歩が分かる短い返答をしてください。"
            "実行可能な場合は何が実行されるかを伝え、未実装や改造案の場合はCodex依頼案として確認できることを伝えてください。"
        ),
    }
    return json.dumps(context, ensure_ascii=False)


def _extract_response_text(response: Any) -> str | None:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    output = getattr(response, "output", None)
    if not output:
        return None
    parts: list[str] = []
    for item in output:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if isinstance(text, str):
                parts.append(text)
    text = "\n".join(parts).strip()
    return text or None


def _load_recent_session_context(session_id: str, limit: int = 6) -> list[dict[str, str]]:
    safe_session_id = SESSION_ID_PATTERN.sub("_", session_id.strip())[:80] if session_id else ""
    if not safe_session_id:
        return []

    log_path = SESSION_LOG_DIR / f"session_{safe_session_id}.jsonl"
    if not log_path.exists():
        return []

    records: list[dict[str, str]] = []
    try:
        lines = log_path.read_text(encoding="utf-8").splitlines()[-limit:]
    except OSError:
        return []
    for line in lines:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        message = str(record.get("message") or "").strip()
        reply = str(record.get("reply") or "").strip()
        if message:
            records.append({"role": "student", "content": message})
        if reply:
            records.append({"role": "assistant", "content": reply})
    return records[-limit:]


def _looks_like_general_lab_question(message: str) -> bool:
    return any(
        keyword in message
        for keyword in [
            "何を試",
            "なにを試",
            "何ができ",
            "なにができ",
            "できること",
            "使い方",
            "ヘルプ",
            "help",
            "こんにちは",
        ]
    )


def _looks_like_gravity_ball(message: str) -> bool:
    return any(
        keyword in message
        for keyword in ["重力", "gravity", "落下", "ボール", "ball", "跳ね", "高さ", "height", "反発", "bounce"]
    )


def _looks_like_existing_simulation_change(message: str) -> bool:
    simulation_keywords = ["gravity_ball", "maze_agent", "flocking", "ボール", "迷路", "群れ", "鳥", "魚"]
    change_keywords = ["改造", "変更", "追加", "実装", "作って", "作りたい", "色", "表示", "ログ", "readme", "機能"]
    parameter_only_keywords = ["重力", "高さ", "反発", "個体", "まとまり", "向き合わせ", "距離確保", "ランダム"]
    if not any(keyword in message for keyword in simulation_keywords):
        return False
    if not any(keyword in message for keyword in change_keywords):
        return False
    if any(keyword in message for keyword in parameter_only_keywords) and not any(
        keyword in message for keyword in ["色", "表示", "ログ", "readme", "機能", "追加", "実装", "改造"]
    ):
        return False
    return True


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


def _existing_simulation_change_spec(message: str, normalized: str) -> dict[str, Any]:
    simulation_name = "new_simulation"
    objects = ["既存シミュレーションの登場物", "変更対象"]
    if any(keyword in normalized for keyword in ["gravity_ball", "ボール"]):
        simulation_name = "gravity_ball"
        objects = ["ボール", "床", "軌跡", "変更対象"]
    elif any(keyword in normalized for keyword in ["maze_agent", "迷路"]):
        simulation_name = "maze_agent"
        objects = ["迷路", "壁", "エージェント", "ゴール", "変更対象"]
    elif any(keyword in normalized for keyword in ["flocking", "群れ", "鳥", "魚"]):
        simulation_name = "flocking"
        objects = ["群れエージェント", "移動範囲", "変更対象"]

    return {
        "title": f"{simulation_name} の小改造案",
        "simulation_name": simulation_name,
        "goal": f"学生の入力「{message}」に基づき、既存シミュレーションへ小さな変更を加える",
        "source_message": message,
        "objects": objects,
        "parameters": {
            "requested_change": message,
            "scope": "既存シミュレーションの小改造",
        },
        "observations": ["変更前後で見た目または挙動がどう変わったか", "既存の実行・再生が壊れていないか"],
        "phase": "Phase 6a Codex依頼案",
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
