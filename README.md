# 3D-AI Lab

3D-AI Lab は、学生向けの小さなAI入門ツールです。
このMVPでは、ブラウザ上の3D空間、ラボ助手チャット、FastAPI連携、会話ログ保存に加えて、Phase 4〜5 の `gravity_ball`、Phase 7a の `maze_agent`、Phase 7b の `flocking` シミュレーションを実行・再生できます。

APIキーなしでもルールベース版のラボ助手として動きます。
`.env` に `OPENAI_API_KEY` を設定した場合は、OpenAI APIを使った自然なラボ助手応答に切り替わります。

## 実装済みの機能

- ブラウザ上に Three.js の3Dラボ空間を表示する
- 簡単なラボ助手アバターと吹き出しを表示する
- 学生の入力を Python/FastAPI バックエンドの `POST /chat` に送信する
- 会話ログを `logs/sessions/` に JSONL 形式で保存する
- APIキーなしのルールベース版ラボ助手が、学生の入力を実験案に分解する
- Codex向けタスク案を生成する
- Codex向けタスク案を確認・保存・コピーできる
- `gravity_ball` を実行し、`result.json` を生成する
- 生成されたボールの落下・反発シミュレーションを3D空間で再生する
- `maze_agent` を実行し、固定迷路をエージェントが進む様子を3D空間で再生する
- `flocking` を実行し、複数エージェントのBoids風の群れ行動を3D空間で再生する
- マウス操作で3D視点を回転、ズーム、パンする
- 重力、初期高さ、反発係数をUIまたは簡単なチャット指示で変更する
- チャットで迷路系の指示を入力すると、`maze_agent` を自動実行する
- チャットで群れ、鳥、魚、flocking、boids 系の指示を入力すると、`flocking` を自動実行する

## 必要なもの

- Python 3.11 以上を推奨
- Windows環境では `py` コマンドで通常のPythonを指定することを推奨
- Three.js をCDNから読み込むためのインターネット接続

## セットアップ

PowerShellで以下を実行します。

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

`python -m venv .venv` で LibreOffice の Python が使われて失敗した場合は、壊れた `.venv` を削除してから作り直してください。

```powershell
Remove-Item -Recurse -Force .venv
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

PowerShellで仮想環境の有効化がブロックされる場合は、次を実行してから再度有効化してください。

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 起動方法

```powershell
python -m uvicorn backend.app:app --reload
```

起動後、ブラウザで以下を開きます。

```text
http://127.0.0.1:8000/
```

仮想環境を有効化している場合は、次の形式でも起動できます。

```powershell
uvicorn backend.app:app --reload
```

## OpenAI APIを使う場合

OpenAI APIを使う場合は、プロジェクト直下に `.env` を作成します。
`.env` はGit管理対象外です。

```env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4.1-mini
OPENAI_ENABLED=true
OPENAI_TIMEOUT_SECONDS=20
```

設定後、FastAPIサーバを再起動してください。

```powershell
python -m uvicorn backend.app:app --reload
```

APIキーがない、`OPENAI_ENABLED=false`、API呼び出しに失敗した、依存関係が未インストール、のいずれかの場合は、従来のルールベース応答に自動で戻ります。
OpenAI APIはバックエンドからのみ呼び出し、フロントエンドのHTMLやJavaScriptにはAPIキーを置きません。

## gravity_ball の使い方

3D空間はマウスで視点変更できます。

- 左ドラッグ: 視点を回転
- ホイール: ズーム
- 右ドラッグ: 平行移動

画面右側の `gravity_ball` パネルで、以下を変更できます。

- `重力`: 数値を大きくすると速く落ちる
- `初期高さ`: 数値を大きくすると高い位置から落ちる
- `反発係数`: 数値を大きくするとよく跳ねる
- `再生速度`: アニメーションの再生速度

`実行` を押すと FastAPI がシミュレーションを再実行し、`simulations/gravity_ball/result.json` を更新します。

チャット欄に次のような文を入力しても、簡単なキーワード判定でパラメータが反映されます。

```text
重力を強くして
重力を3にして
高いところからボールを落として
高さを7にして
よく跳ねるボールにして
反発係数を0.4にして
```

## Phase 7a: maze_agent の使い方

画面右側のシミュレーション選択で `maze_agent` を選び、`実行` を押します。
固定迷路またはランダム迷路で、エージェントがBFS系の軽量探索で求めた経路に沿ってスタートからゴールへ進みます。

操作ボタンは `gravity_ball` と共通です。

- `実行`: 迷路シミュレーションを再生成して再生する
- `再生` / `一時停止`: アニメーションを開始・停止する
- `リセット`: 最初のフレームに戻す
- `ステップ`: 1フレーム進める
- `再生速度`: 0.5x、1x、2x、4x を切り替える

`maze_agent` では次も変更できます。

- `ランダム迷路を生成`: オンにすると毎回違う迷路を生成する
- `迷路サイズ`: 7x7、9x9、11x11
- `壁の多さ`: 大きいほど壁が増える
- `シード`: 同じ番号なら同じランダム迷路を再現する。空なら毎回変わる

チャット欄に次のような文を入力しても、自動で `maze_agent` に切り替えて実行します。

```text
迷路をエージェントが進む
迷路のゴールまで進んで
迷路をエージェントが学習しながら進む
ランダムな迷路をエージェントが進む
```

Phase 7a の `maze_agent` は、強化学習ではありません。
まず確実に3D表示できる軽量探索として実装しています。
強化学習による方策更新や報酬推移の可視化は後続フェーズの範囲です。

## Phase 7b: flocking の使い方

画面右側のシミュレーション選択で `flocking` を選び、`実行` を押します。
複数の小さな円錐が、進行方向を向きながら3D空間内を移動します。

`flocking` は強化学習ではなく、Boids風の簡易ルールで実装しています。

- `群れのまとまり`: 近くの個体の中心へ寄る強さ
- `向き合わせ`: 近くの個体の速度方向へ揃える強さ
- `距離確保`: 近すぎる個体から離れる強さ
- `個体数`: 表示するエージェント数
- `シード`: 同じ初期配置と軌道を再現するための番号

チャット欄に次のような文を入れても、自動で `flocking` に切り替えて実行します。

```text
鳥の群れを動かして
魚の群れを表示して
たくさんの個体で群れを作って
まとまった群れにして
ばらける群れにして
```

観察ポイントは、群れのまとまり方、進行方向の揃い方、近すぎる個体が離れる様子、重みを変えたときの軌道の違いです。

## Phase 3: ラボ助手

Phase 3は、APIキーなしのルールベース実装です。
実際のLLMはまだ呼び出しません。

チャット欄に入力すると、ラボ助手は以下を返します。

- 自然文の返答
- 実験案
- 変更できるパラメータ
- 観察ポイント
- Codex向けタスク案

`gravity_ball` に関する入力は、実行可能なシミュレーションとして扱われます。
たとえば `重力を3にして` は `gravity=3.0` として反映されます。

`迷路をエージェントが学習しながら進む` のような迷路系の題材は、Phase 7a の `maze_agent` として軽量探索を実行します。
強化学習そのものは後続フェーズとして案内します。

Codex向けタスク案は生成するだけで、自動実装は行いません。
自動実装はPhase 6以降の範囲です。

## Phase 6a: Codex依頼準備

Phase 6aでは、ラボ助手が生成したCodex向けタスク案を、画面右側の `Codex依頼案` パネルで確認できます。

できること:

- 最新のCodex向けタスク文を確認する
- タスク文を `logs/codex_tasks/tasks.jsonl` に保存する
- タスク文をクリップボードへコピーする
- 同じセッションで保存した依頼案の履歴を見る

Phase 6aでは、Codexによる自動実装、ソースコード変更、コマンド実行、Git操作は行いません。
学生または教員が内容を確認し、必要な場合に手動でCodexへ渡します。
既存シミュレーションの小改造の半自動化は Phase 6b の範囲です。

## APIの簡単な確認

チャットAPI:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/chat `
  -ContentType "application/json; charset=utf-8" `
  -Body '{"message":"重力を強くして"}'
```

シミュレーション実行API:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/simulations/gravity_ball/run `
  -ContentType "application/json" `
  -Body '{"gravity":16.0,"initial_height":6.0,"bounce":0.8,"steps":360,"dt":0.016}'
```

最新結果の取得:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/simulations/gravity_ball/result
```

迷路シミュレーション実行API:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/simulations/maze_agent/run `
  -ContentType "application/json" `
  -Body '{"grid_size":9,"steps_per_cell":12,"dt":0.08,"show_search":false,"randomize":true,"wall_density":0.32}'
```

迷路の最新結果の取得:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/simulations/maze_agent/result
```

群れ行動シミュレーション実行API:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/simulations/flocking/run `
  -ContentType "application/json" `
  -Body '{"agent_count":30,"steps":360,"dt":0.08,"seed":123,"cohesion_weight":0.55,"alignment_weight":0.65,"separation_weight":1.25,"perception_radius":2.2,"separation_radius":0.7,"bounds":6.0}'
```

群れ行動の最新結果の取得:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/simulations/flocking/result
```

Codex依頼案の保存:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/codex-tasks `
  -ContentType "application/json; charset=utf-8" `
  -Body '{"session_id":"demo","source_message":"感染シミュレーションを作りたい","experiment_spec":{"title":"感染シミュレーション案","simulation_name":"infection_sim","goal":"感染が広がる様子を観察する"},"codex_task":"infection_sim を小さく実装するタスク案"}'
```

Codex依頼案の取得:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/codex-tasks?session_id=demo&limit=5"
```

## ログ

チャット内容は、次の形式で追記保存されます。

```text
logs/sessions/session_<session_id>.jsonl
```

シミュレーション実行ログは、次の形式で追記保存されます。

```text
logs/experiments/gravity_ball.jsonl
logs/experiments/maze_agent.jsonl
logs/experiments/flocking.jsonl
```

Codex依頼案ログは、次の形式で追記保存されます。

```text
logs/codex_tasks/tasks.jsonl
```

実行時に作られるJSONLログはGit管理対象外です。

## ディレクトリ構成

```text
backend/
  app.py
  llm_client.py
  schemas.py
frontend/
  index.html
  src/
    api_client.js
    avatar.js
    lab_ui.js
    main.js
    simulation_viewer.js
simulations/
  gravity_ball/
    config.json
    sim.py
    result.json
    README.md
  maze_agent/
    config.json
    sim.py
    result.json
    README.md
  flocking/
    config.json
    sim.py
    result.json
    README.md
logs/
  sessions/
  experiments/
  codex_tasks/
requirements.txt
```

## 今後のLLM連携

将来、実際のLLMと接続する場合は `backend/llm_client.py` を差し替えます。
`/chat` のAPI形状は保ち、`generate_reply()` の中身を実LLM呼び出しに置き換える想定です。
