from __future__ import annotations

from typing import Any


def build_codex_task(experiment_spec: dict[str, Any]) -> str:
    title = experiment_spec.get("title", "3D-AI Lab experiment")
    simulation_name = experiment_spec.get("simulation_name", "new_simulation")
    goal = experiment_spec.get("goal", "学生が観察できる小さな3Dシミュレーションを作る")
    objects = experiment_spec.get("objects", [])
    parameters = experiment_spec.get("parameters", {})
    observations = experiment_spec.get("observations", [])

    object_lines = "\n".join(f"- {item}" for item in objects) or "- 必要な3Dオブジェクトを最小構成で定義する"
    parameter_lines = "\n".join(f"- {key}: {value}" for key, value in parameters.items()) or "- 変更可能なパラメータをconfig.jsonに置く"
    observation_lines = "\n".join(f"- {item}" for item in observations) or "- 位置や状態変化を3D空間で観察できるようにする"

    return f"""3D-AI Lab の実装タスク案です。

目的:
{goal}

対象シミュレーション:
{simulation_name}

実装方針:
- simulations/{simulation_name}/ に config.json, sim.py, result.json, README.md を用意する
- sim.py は result.json 形式で objects と frames を生成する
- フロントエンドの共通ビューアで表示できるJSON構造を保つ
- 既存の /chat と gravity_ball の動作を壊さない

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

