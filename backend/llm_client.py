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
    experiment_spec: dict[str, Any] | None
    codex_task: str | None
    assistant_notes: list[str]
    suggested_action: str | None = None
    simulation_params: dict[str, float | int | bool] | None = None
    use_openai: bool = True


def generate_lab_assistant_response(message: str, session_id: str) -> LabAssistantResponse:
    rule_response = _generate_rule_based_response(message=message, session_id=session_id)
    if not rule_response.use_openai or not _openai_enabled():
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
        return LabAssistantResponse(
            reply="まずは試したいことを一文で入力してみましょう。",
            experiment_spec=None,
            codex_task=None,
            assistant_notes=["入力が空だったため、最小の実験案を返しました。"],
        )

    normalized = unicodedata.normalize("NFKC", cleaned).lower()
    if _looks_like_confirmation(normalized):
        pending_spec = _load_pending_experiment_spec(session_id)
        if pending_spec:
            return LabAssistantResponse(
                reply=(
                    "分かりました。この内容でCodex向けの実装依頼案を作りました。"
                    "内容を確認して、必要なら保存・コピーしてください。"
                ),
                experiment_spec=pending_spec,
                codex_task=build_codex_task(pending_spec),
                assistant_notes=["確認を受けてCodex依頼案を作成しました。"],
            )
        return LabAssistantResponse(
            reply="どの機能やシミュレーションを作るか、もう少し具体的に教えてください。",
            experiment_spec=None,
            codex_task=None,
            assistant_notes=["確認対象が見つからなかったため、追加説明を依頼しました。"],
        )

    if _looks_like_existing_simulation_change(normalized):
        spec = _existing_simulation_change_spec(cleaned, normalized)
        is_visual_customization = _looks_like_visual_customization(normalized)
        return LabAssistantResponse(
            reply=_existing_simulation_change_reply(is_visual_customization),
            experiment_spec=spec,
            codex_task=build_codex_task(spec),
            assistant_notes=_existing_simulation_change_notes(is_visual_customization),
        )

    if _looks_like_ui_change_request(normalized):
        spec = _app_ui_feature_spec(cleaned)
        return LabAssistantResponse(
            reply=(
                "3D-AI Labの画面や操作UIの変更として整理しました。"
                "Codex向けの依頼案を作ったので、内容を確認して必要なら保存・コピーしてください。"
            ),
            experiment_spec=spec,
            codex_task=build_codex_task(spec),
            assistant_notes=["UI変更依頼として返しました。"],
        )

    if _looks_like_current_info_question(normalized):
        return LabAssistantResponse(
            reply=(
                "わたしは、インターネットや外部のリアルタイム情報を参照していないので、その現在値を確定して答えられません。"
                "必要なら、その情報を画面に表示するUI機能追加の依頼案を作れます。"
            ),
            experiment_spec=None,
            codex_task=None,
            assistant_notes=["リアルタイム情報に関する一般質問として返しました。"],
        )

    if _looks_like_general_lab_question(normalized):
        return LabAssistantResponse(
            reply=(
                "今は gravity_ball, maze_agent, flocking を試せます。"
                "重力や高さを変える、迷路をランダム生成する、群れの個体数やまとまりを変える、といった指示をチャットから送れます。"
            ),
            experiment_spec=None,
            codex_task=None,
            assistant_notes=["一般的な使い方案内として返しました。"],
        )

    if _looks_like_general_conversation(normalized):
        return LabAssistantResponse(
            reply=(
                "私は3D-AI Labのラボ助手です。"
                "質問に答えたり、既存シミュレーションの使い方を案内したり、実装依頼を整理したりできます。"
            ),
            experiment_spec=None,
            codex_task=None,
            assistant_notes=["一般的な会話として返しました。"],
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
                "gravity_ball は実行可能なため、実行アクションも返します。",
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
                "flocking は実行可能です。",
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
                "現在は強化学習ではなく軽量探索で、スタートからゴールへ進む様子を実行して表示します。"
            ),
            experiment_spec=spec,
            codex_task=build_codex_task(spec),
            assistant_notes=[
                "maze_agent は実行可能です。",
                "強化学習は今後の拡張候補として扱い、今回は固定迷路のBFS系探索として実行します。"
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

    if not _looks_like_simulation_creation_request(normalized):
        return LabAssistantResponse(
            reply="質問や相談として受け取りました。必要なら、UI変更かシミュレーション依頼として整理することもできます。",
            experiment_spec=None,
            codex_task=None,
            assistant_notes=["一般的な会話として返しました。"],
        )

    spec = _generic_experiment_spec(cleaned)
    return LabAssistantResponse(
        reply=(
            f"「{cleaned}」のシミュレーションを実装する依頼案を作りますか？"
            "作る場合は「はい」または「お願いします」と入力してください。"
        ),
        experiment_spec=spec,
        codex_task=None,
        assistant_notes=[
            "未対応の題材のため、実装依頼案を作る前に確認待ちにしました。",
            "シミュレーション実装確認待ち",
        ],
        use_openai=False,
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
学生に一方的に講義する先生ではなく、学生の質問や「試したいこと」を一緒に整理する助手として振る舞ってください。

重要な制約:
- 返答は日本語で、初心者向けに短く具体的にしてください。
- ユーザーが一般的な会話や質問をしている場合は、無理に3D実験やシミュレーションへ変換せず、普通に答えてください。
- まず「一般会話」「3D-AI LabのUI変更」「シミュレーション依頼」のどれかとして考えてください。
- 日付、時刻、天気、気温、湿度、風速などの現在値を聞かれた場合は一般会話として扱い、現在値を推測したり断定したりせず、わたしはインターネットや外部のリアルタイム情報を参照していないため確定して答えられない、と一人称で答えてください。
- 日付、時刻、天気、気温、湿度、風速などを画面に表示する機能追加を明確に依頼された場合は、一般質問として断らず、3D-AI LabのUI変更としてCodex向け依頼案を用意したことを伝えてください。
- 画面、パネル、ボタン、チャット欄などの変更依頼は、シミュレーションではなく3D-AI LabのUI変更として扱ってください。
- 新しいシミュレーションや大きな実装依頼は、ユーザーが明確に確認する前に実装案を確定したように言わないでください。
- 実行可能な既存シミュレーションは gravity_ball, maze_agent, flocking です。
- 既存シミュレーションの色や表示設定など、許可済みの小改造だけを確認後に限定適用できます。
- 新規シミュレーション作成、自由なコード編集、Git操作、任意コマンド実行は行いません。
- APIキー、内部実装、環境変数の値は説明しないでください。
- 返答は自然文だけにしてください。JSONやMarkdown表は不要です。
- 既存の構造化判定結果に反するアクションを約束しないでください。
- 内部の開発段階名や番号は、ユーザーへの返答に出さないでください。
"""


def _build_openai_user_context(
    *,
    message: str,
    session_id: str,
    rule_response: LabAssistantResponse,
) -> str:
    context = {
        "student_message": message,
        "intent": _intent_label(message, rule_response),
        "available_capabilities": _available_capabilities_for_openai(),
        "recent_conversation": _recent_context_for_openai(session_id, rule_response),
        "draft_reply": rule_response.reply,
        "structured_interpretation": {
            "suggested_action": rule_response.suggested_action,
            "simulation_params": rule_response.simulation_params,
            "experiment_spec": rule_response.experiment_spec,
            "codex_task": rule_response.codex_task,
            "assistant_notes": rule_response.assistant_notes,
        },
        "reply_goal": (
            "上の構造化判定を踏まえて、学生に次の一歩が分かる短い返答をしてください。"
            "draft_reply は現在の質問に対する基準回答です。内容の種類、対象、制約を変えず、必要なら表現だけ自然に整えてください。"
            "直近の会話より現在の student_message と structured_interpretation を優先し、現在の依頼に含まれない過去の機能案やCodex依頼案を持ち出さないでください。"
            "intent が capability_question なら、リアルタイム情報の制限ではなく、available_capabilities と draft_reply を参照して3D-AI Labでできることを答えてください。"
            "experiment_spec が null の場合は一般会話として自然に答え、実験案やCodex依頼案に無理に誘導しないでください。"
            "assistant_notes に「リアルタイム情報に関する一般質問」がある場合は、現在値を推測せず、structured_interpretation の方針を自然な一人称の文章に整えてください。"
            "assistant_notes に「UI変更依頼」がある場合は、シミュレーション実行ではなくCodex向け依頼案を用意したことを短く伝えてください。"
            "実行可能な場合は何が実行されるかを伝え、未実装や改造案の場合はCodex依頼案として確認できることを伝えてください。"
        ),
    }
    return json.dumps(context, ensure_ascii=False)


def _intent_label(message: str, rule_response: LabAssistantResponse) -> str:
    normalized = unicodedata.normalize("NFKC", message.strip()).lower()
    notes = " ".join(rule_response.assistant_notes)
    if _looks_like_capability_question(normalized):
        return "capability_question"
    if "UI変更依頼" in notes:
        return "ui_change_request"
    if "リアルタイム情報に関する一般質問" in notes:
        return "general_realtime_info_question"
    if rule_response.suggested_action:
        return "runnable_simulation"
    if rule_response.experiment_spec and not rule_response.codex_task:
        return "simulation_request_pending_confirmation"
    if rule_response.codex_task:
        return "codex_task_draft"
    return "general_conversation"


def _available_capabilities_for_openai() -> list[str]:
    return [
        "3D空間でラボ助手アバターとシミュレーションを表示できます。",
        "gravity_ball で重力、初期高さ、反発係数を変えてボールの落下と反発を観察できます。",
        "maze_agent で固定迷路またはランダム迷路をエージェントが進む様子を再生できます。",
        "flocking で複数エージェントのBoids風の群れ行動を観察できます。",
        "チャットから既存シミュレーションの条件変更や実行を依頼できます。",
        "画面や操作UIの変更依頼はCodex向け依頼案として整理し、保存・コピーできます。",
        "未対応の新規シミュレーション依頼は、実装依頼案を作る前に確認を取ります。",
        "既存シミュレーションの色など、許可済みの小改造はプレビュー後に限定適用できます。",
        "初期状態ボタンで見た目変更、最新結果、画面上の操作状態を既定値に戻せます。",
    ]


def _recent_context_for_openai(session_id: str, rule_response: LabAssistantResponse) -> list[dict[str, str]]:
    notes = " ".join(rule_response.assistant_notes)
    if any(
        marker in notes
        for marker in [
            "一般的な使い方案内",
            "一般的な会話",
            "リアルタイム情報に関する一般質問",
            "UI変更依頼",
        ]
    ):
        return []
    return _load_recent_session_context(session_id)


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


def _load_pending_experiment_spec(session_id: str) -> dict[str, Any] | None:
    safe_session_id = SESSION_ID_PATTERN.sub("_", session_id.strip())[:80] if session_id else ""
    if not safe_session_id:
        return None

    log_path = SESSION_LOG_DIR / f"session_{safe_session_id}.jsonl"
    if not log_path.exists():
        return None

    try:
        lines = log_path.read_text(encoding="utf-8").splitlines()[-8:]
    except OSError:
        return None

    for line in reversed(lines):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        notes = record.get("assistant_notes") or []
        spec = record.get("experiment_spec")
        if isinstance(spec, dict) and "シミュレーション実装確認待ち" in notes:
            return spec
    return None


def _looks_like_confirmation(message: str) -> bool:
    return message.strip() in {
        "はい",
        "お願い",
        "お願いします",
        "作って",
        "作成して",
        "実装して",
        "進めて",
        "ok",
        "yes",
        "y",
    }


def _looks_like_current_info_question(message: str) -> bool:
    if not _looks_like_question(message):
        return False
    current_markers = ["今日", "明日", "現在", "いま", "今", "最新", "このあと", "today", "tomorrow", "current", "now"]
    info_targets = [
        "日付",
        "日時",
        "時刻",
        "時間",
        "何時",
        "何日",
        "何月",
        "何曜日",
        "天気",
        "気温",
        "湿度",
        "風速",
        "風向",
        "降水",
        "雨",
        "雪",
        "気圧",
        "花粉",
        "為替",
        "株価",
        "ニュース",
        "date",
        "time",
        "weather",
        "temperature",
        "humidity",
        "wind",
        "news",
    ]
    return any(keyword in message for keyword in current_markers) and any(keyword in message for keyword in info_targets)


def _looks_like_ui_change_request(message: str) -> bool:
    if _mentions_existing_simulation(message):
        return False
    ui_keywords = [
        "ui",
        "画面",
        "パネル",
        "ボタン",
        "チャット欄",
        "吹き出し",
        "入力欄",
        "ヘッダー",
        "サイドバー",
        "ラボ画面",
    ]
    display_info_keywords = [
        "日付",
        "日時",
        "時刻",
        "時間",
        "時計",
        "天気",
        "気温",
        "湿度",
        "風速",
        "風向",
        "降水",
        "気圧",
        "ニュース",
        "date",
        "time",
        "weather",
        "temperature",
        "humidity",
        "wind",
    ]
    feature_keywords = ["表示", "追加", "機能", "実装", "つけ", "付け", "入れ", "作", "変更", "改造", "戻す", "出し"]
    has_ui_target = any(keyword in message for keyword in ui_keywords)
    has_display_target = any(keyword in message for keyword in display_info_keywords)
    has_feature_action = any(keyword in message for keyword in feature_keywords)
    return has_feature_action and (has_ui_target or has_display_target)


def _looks_like_general_lab_question(message: str) -> bool:
    if _looks_like_capability_question(message):
        return True
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


def _looks_like_capability_question(message: str) -> bool:
    return any(
        keyword in message
        for keyword in [
            "何ができ",
            "なにができ",
            "できること",
            "何を試",
            "なにを試",
            "どんなこと",
            "機能一覧",
            "help",
            "ヘルプ",
        ]
    )


def _looks_like_general_conversation(message: str) -> bool:
    if _mentions_existing_simulation(message):
        return _looks_like_question(message) and not _looks_like_existing_simulation_change(message)

    if any(
        keyword in message
        for keyword in [
            "あなたは誰",
            "君は誰",
            "お前は誰",
            "自己紹介",
            "who are you",
            "何者",
            "ありがとう",
            "thanks",
            "こんばんは",
            "おはよう",
            "さようなら",
        ]
    ):
        return True

    return _looks_like_question(message) and not _looks_like_simulation_creation_request(message)


def _looks_like_question(message: str) -> bool:
    return any(
        keyword in message
        for keyword in ["?", "？", "とは", "何", "なに", "誰", "どう", "なぜ", "教えて", "教え", "説明", "わかり", "分かり", "知り"]
    )


def _looks_like_simulation_creation_request(message: str) -> bool:
    return any(keyword in message for keyword in ["シミュレーション", "simulation", "実験", "3d"]) and any(
        keyword in message for keyword in ["作", "実装", "追加", "生成", "表示", "動か"]
    )


def _mentions_existing_simulation(message: str) -> bool:
    return any(keyword in message for keyword in ["gravity_ball", "maze_agent", "flocking", "ボール", "迷路", "群れ", "鳥", "魚"])


def _looks_like_gravity_ball(message: str) -> bool:
    return any(
        keyword in message
        for keyword in ["重力", "gravity", "落下", "ボール", "ball", "跳ね", "高さ", "height", "反発", "bounce"]
    )


def _looks_like_existing_simulation_change(message: str) -> bool:
    simulation_keywords = ["gravity_ball", "maze_agent", "flocking", "ボール", "迷路", "群れ", "鳥", "魚"]
    change_keywords = [
        "改造",
        "変更",
        "追加",
        "拡張",
        "実装",
        "作って",
        "作りたい",
        "色",
        "赤",
        "青",
        "緑",
        "黄色",
        "白",
        "黒",
        "見た目",
        "表示",
        "ログ",
        "readme",
        "機能",
        "学習",
        "強化学習",
        "報酬",
        "障害物",
    ]
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


def _looks_like_visual_customization(message: str) -> bool:
    return any(
        keyword in message
        for keyword in [
            "色",
            "赤",
            "青",
            "緑",
            "黄色",
            "白",
            "黒",
            "見た目",
            "表示",
            "床",
            "壁",
            "軌跡",
            "境界",
            "パレット",
        ]
    )


def _existing_simulation_change_reply(is_visual_customization: bool) -> str:
    if is_visual_customization:
        return (
            "既存シミュレーションの見た目変更として整理しました。"
            "プレビューで内容を確認してから、許可された範囲だけ限定適用できます。"
        )
    return (
        "既存シミュレーションの拡張依頼として整理しました。"
        "この内容はCodex向けの依頼案として確認できます。自動で適用できるのは、今のところ見た目変更などの安全な小改造だけです。"
    )


def _existing_simulation_change_notes(is_visual_customization: bool) -> list[str]:
    if is_visual_customization:
        return [
            "許可済みの見た目変更だけを、プレビュー後に適用できます。",
            "新規シミュレーション作成や自由なコード編集は、今後の拡張または手動Codex依頼の範囲です。",
        ]
    return [
        "機能拡張の依頼案として整理しました。",
        "自動適用できるのは、現時点では見た目変更などの安全な小改造だけです。",
    ]


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
        "status": "実行可能",
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
        "status": "実行可能",
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
        "status": "実行可能",
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
        "status": "Codex依頼案",
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
        "status": "今後の実装候補",
    }


def _date_time_display_feature_spec(message: str) -> dict[str, Any]:
    return {
        "title": "ラボ画面の日付・時刻表示",
        "simulation_name": "lab_ui",
        "goal": "3D-AI Labの画面上で現在の日付と時刻を確認できるようにする",
        "objects": ["3D画面またはヘッダー上の小さな日時表示UI"],
        "parameters": {
            "scope": "アプリUI機能追加",
            "source_message": message,
            "display_format": "日本語環境で読みやすい日付と時刻",
            "update_interval": "1秒または1分ごとに更新",
        },
        "observations": [
            "画面を見れば現在の日時が分かる",
            "チャット欄やシミュレーション操作UIを邪魔しない",
            "リロード後も自然に表示される",
        ],
        "status": "Codex依頼案",
    }


def _weather_display_feature_spec(message: str) -> dict[str, Any]:
    return {
        "title": "ラボ画面の天気表示",
        "simulation_name": "lab_ui",
        "goal": "3D-AI Labの画面上で天気情報を確認できるようにする",
        "objects": ["3D画面またはヘッダー上の小さな天気表示UI"],
        "parameters": {
            "scope": "アプリUI機能追加",
            "source_message": message,
            "data_source": "外部天気APIまたは手入力の候補。APIキーや通信仕様は実装前に確認する",
            "display_format": "地域、天気、気温、更新時刻を読みやすく表示",
        },
        "observations": [
            "画面を見れば天気情報の有無が分かる",
            "API未設定時に分かりやすい案内を表示する",
            "チャット欄やシミュレーション操作UIを邪魔しない",
        ],
        "status": "Codex依頼案",
    }


def _app_ui_feature_spec(message: str) -> dict[str, Any]:
    return {
        "title": "3D-AI Lab UI機能追加",
        "simulation_name": "lab_ui",
        "goal": f"学生の入力「{message}」に基づき、3D-AI Labの画面や操作UIを改善する",
        "objects": ["既存の3D画面", "右側パネル", "チャット欄", "必要なUI部品"],
        "parameters": {
            "scope": "アプリUI機能追加",
            "source_message": message,
            "safety": "既存の3D表示、チャット、シミュレーション操作を壊さない",
        },
        "observations": [
            "画面上で変更内容が確認できる",
            "既存の操作が維持される",
            "狭い画面でもUIが重ならない",
        ],
        "status": "Codex依頼案",
    }


def _default_experiment_spec() -> dict[str, Any]:
    return {
        "title": "最小実験案",
        "simulation_name": "gravity_ball",
        "goal": "重力で落ちるボールを観察する",
        "objects": ["ボール", "床"],
        "parameters": {"gravity": "変更可能", "initial_height": "変更可能", "bounce": "変更可能"},
        "observations": ["落下速度", "跳ね返り"],
        "status": "実行可能",
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
