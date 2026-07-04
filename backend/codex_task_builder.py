from __future__ import annotations

from typing import Any


def build_codex_task(experiment_spec: dict[str, Any]) -> str:
    title = experiment_spec.get("title", "3D-AI Lab experiment")
    simulation_name = experiment_spec.get("simulation_name", "new_simulation")
    goal = experiment_spec.get("goal", "学生が観察できる小さな3Dシミュレーションを作る")
    objects = experiment_spec.get("objects", [])
    parameters = experiment_spec.get("parameters", {})
    observations = experiment_spec.get("observations", [])
    is_existing_change = parameters.get("scope") == "既存シミュレーションの小改造"
    is_app_ui_feature = parameters.get("scope") == "アプリUI機能追加"

    object_lines = "\n".join(f"- {item}" for item in objects) or "- 必要な3Dオブジェクトを最小構成で定義する"
    parameter_lines = "\n".join(f"- {key}: {value}" for key, value in parameters.items()) or "- 変更可能なパラメータをconfig.jsonに置く"
    observation_lines = "\n".join(f"- {item}" for item in observations) or "- 位置や状態変化を3D空間で観察できるようにする"
    if is_app_ui_feature:
        implementation_lines = """- frontend/index.html と frontend/src/*.js の既存構成を確認する
- 依頼内容に合うUI部品、表示欄、または操作部品を小さく追加する
- 日時などブラウザ側で取得できる情報はブラウザAPIで扱い、外部通信を増やさない
- 天気など外部情報が必要な場合は、APIキーをフロントエンドに置かず、未設定時の表示も用意する
- 表示は定期更新し、リロード後も自然に初期化されるようにする
- 既存の3D表示、チャット、シミュレーション操作、初期状態ボタンを壊さない
- READMEに使い方と仕様を追記する"""
    elif is_existing_change:
        implementation_lines = f"""- simulations/{simulation_name}/ の既存ファイルを確認する
- 変更は小さく保ち、既存の result.json 形式を壊さない
- 必要なら config.json に変更可能なパラメータを追加する
- sim.py を変更した場合は result.json を再生成する
- READMEに変更内容と観察ポイントを追記する"""
    else:
        implementation_lines = f"""- simulations/{simulation_name}/ に config.json, sim.py, result.json, README.md を用意する
- sim.py は result.json 形式で objects と frames を生成する
- フロントエンドの共通ビューアで表示できるJSON構造を保つ
- 既存の /chat と gravity_ball の動作を壊さない"""

    return f"""3D-AI Lab の実装タスク案です。
現在の3D-AI Labでは、既存シミュレーションの色や表示設定など、許可済みの小改造だけを確認後に限定適用できます。
新規シミュレーション作成や自由なコード編集は、学生または教員が内容を確認してから手動でCodexに渡してください。

目的:
{goal}

対象シミュレーション:
{simulation_name}

実装方針:
{implementation_lines}

登場物:
{object_lines}

変更可能なパラメータ:
{parameter_lines}

観察ポイント:
{observation_lines}

READMEに追記すること:
- 実行方法
- 変更できるパラメータ
- 学生が観察すべきポイント
"""
