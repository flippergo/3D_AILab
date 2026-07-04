# Codex向けタスク文テンプレート

目的:
{goal}

対象シミュレーション:
{simulation_name}

作業内容:
- `simulations/{simulation_name}/config.json` を用意する
- `simulations/{simulation_name}/sim.py` を実装する
- `simulations/{simulation_name}/result.json` を生成する
- 3D-AI Lab の共通 result.json 形式に合わせる
- READMEに使い方と観察ポイントを追記する

制約:
- 既存のフロントエンドと `/chat` を壊さない
- まず小さく動くものを優先する
- 外部APIキーは使わない

