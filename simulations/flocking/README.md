# flocking

`flocking` は Phase 7b の発展シミュレーションです。

複数のエージェントが Boids 風の簡易ルールで群れ行動します。
強化学習ではなく、近くの仲間へ寄る、向きを合わせる、近すぎる仲間から離れる、範囲内へ戻る、というルールベースのデモです。

## パラメータ

- `agent_count`: 個体数です。
- `steps`: 生成するフレーム数です。
- `dt`: 1フレームあたりの時間です。
- `seed`: 同じ初期配置を再現するための番号です。空の場合は毎回変わります。
- `cohesion_weight`: 群れのまとまりやすさです。
- `alignment_weight`: 進行方向の揃いやすさです。
- `separation_weight`: 近すぎる個体から離れる強さです。
- `perception_radius`: 近くの仲間として見る範囲です。
- `separation_radius`: 離れようとする距離です。
- `bounds`: 群れが動く範囲です。

## 観察ポイント

- 個体数を増やしたときの群れのまとまり
- `cohesion_weight` と `separation_weight` のバランス
- 同じ `seed` で同じ動きが再現されること
