# gravity_ball

Phase 4〜5 用の最小シミュレーションです。

ボールを一定の重力で落下させ、床に当たると反発係数に応じて跳ね返します。結果は `result.json` に保存され、フロントエンドのThree.jsビューアで再生されます。

主なパラメータ:

- `gravity`: 重力加速度
- `initial_height`: 初期高さ
- `bounce`: 反発係数
- `steps`: シミュレーションのフレーム数
- `dt`: 1ステップの時間

## 実行方法

```powershell
python -m simulations.gravity_ball.sim
```

実行すると `config.json` と `customization.json` の設定を使って `result.json` を再生成します。

## 変更できる表示パラメータ

`customization.json` の `visuals` で表示を調整できます。

- `ball_color`: 単色表示時のボール色、または虹色表示時の代表色
- `ball_color_mode`: `solid` なら単色、`rainbow` なら虹色のボール
- `ball_palette`: 虹色表示で使う色の並び
- `floor_color`: 床の色
- `trajectory_color`: 軌跡の色

今回の小改造では、ボールを `rainbow` モードにして虹色で表示します。重力、反発係数、軌跡、床の動作は既存シミュレーションのままです。

## 観察ポイント

- ボールが虹色で表示され、床や軌跡の色が変わっていないか
- 再生、停止、1ステップ送り、初期状態への復帰がこれまで通り動くか
- `result.json` の `frames` と `summary` が生成され、既存ビューアで読み込めるか
