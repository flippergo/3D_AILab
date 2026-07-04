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
- 保存済みCodex依頼案をCodex実装待ちキューに登録できる
- 保存済みCodex依頼案から、既存シミュレーションの見た目変更をプレビュー・限定適用できる
- `gravity_ball` を実行し、`result.json` を生成する
- 生成されたボールの落下・反発シミュレーションを3D空間で再生する
- `maze_agent` を実行し、固定迷路をエージェントが進む様子を3D空間で再生する
- `flocking` を実行し、複数エージェントのBoids風の群れ行動を3D空間で再生する
- マウス操作で3D視点を回転、ズーム、パンする
- 画面右側にブラウザの現在日時を表示する
- 3D画面左下の `初期状態` ボタンで、見た目変更・最新シミュレーション結果・画面上の操作状態を既定値に戻す
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

## 画面日時表示の使い方

アプリを起動して `http://127.0.0.1:8000/` を開くと、画面右側のヘッダーにブラウザの現在日時が表示されます。
日時はフロントエンドのブラウザAPIで取得し、外部通信は行いません。表示は1秒ごとに更新され、リロード後も自動で初期化されます。Three.jsのCDN読み込みより独立しているため、日時表示だけで外部通信を増やしません。

変更できるパラメータ:

- OSまたはブラウザのタイムゾーン、日付、時刻設定
- ブラウザのロケール表示設定

学生が観察すべきポイント:

- 秒表示が定期的に更新されること
- ページをリロードしても現在日時が自然に再表示されること
- 右側パネルが狭い場合でも、日時表示が他の操作UIやチャット欄と重ならないこと

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

Codex向けタスク案は、まず確認・保存・コピーできる形で生成します。
既存シミュレーションの見た目変更に限り、保存後にプレビューして限定適用できます。

## Codex依頼準備

ラボ助手が生成したCodex向けタスク案は、画面右側の `Codex依頼案` パネルで確認できます。

できること:

- 最新のCodex向けタスク文を確認する
- タスク文を `logs/codex_tasks/tasks.jsonl` に保存する
- タスク文をクリップボードへコピーする
- 保存済み依頼案を `logs/codex_tasks/pending_implementation/` にCodex実装待ちとして出力する
- 同じセッションで保存した依頼案の履歴を見る

この段階では、Codexによる自由な自動実装、任意コマンド実行、Git操作は行いません。
学生または教員が内容を確認し、必要な場合に手動でCodexへ渡します。
既存シミュレーションの見た目変更だけは、保存後に確認付きで限定適用できます。

Codexが使える環境で作業している場合は、依頼案を保存したあと `実装依頼` を押します。
すると、次の形式でCodexが読める実装待ちファイルが作られます。

```text
logs/codex_tasks/pending_implementation/<timestamp>_<task_id>.md
```

毎回Codexへ手で依頼したくない場合は、別のPowerShellでwatcherを起動しておきます。

```powershell
.\.venv\Scripts\python.exe tools\codex_task_watcher.py
```

watcherは `logs/codex_tasks/pending_implementation/` を監視し、新しい実装待ちファイルを見つけると、既定では `codex exec --sandbox danger-full-access` に渡します。
これにより、通常は `保存` → `実装依頼` まで操作すれば、Codex側の実装作業が始まります。
停止するときは watcher を起動しているPowerShellで `Ctrl+C` を押します。

このwatcherは、Codexを使う本人だけが動かす信頼済みローカル環境を前提にしています。
Windows環境では `--sandbox workspace-write` のサンドボックス補助プロセス起動に失敗することがあるため、既定ではサンドボックス初期化を通らない設定にしています。
サンドボックス付きで試したい場合は、次のように明示してください。

```powershell
.\.venv\Scripts\python.exe tools\codex_task_watcher.py --sandbox workspace-write
```

Windows Store版のCodexアプリに同梱されている `codex.exe` は、環境によってPowerShellやPythonから直接起動できない場合があります。
その場合は、別途Codex CLIをインストールしてからwatcherを起動します。

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://chatgpt.com/codex/install.ps1 | iex"
```

インストール後、別のPowerShellで `codex --version` が動くことを確認してください。

動作確認だけしたい場合:

```powershell
.\.venv\Scripts\python.exe tools\codex_task_watcher.py --once --dry-run
```

watcherの処理状態は `logs/codex_tasks/watcher_state.json` に保存されます。
同じ依頼を再実行したい場合は、この状態ファイルから対象の記録を削除するか、状態ファイルを削除してからwatcherを起動し直します。
Codex CLIの実行中ログは `logs/codex_tasks/watcher_outputs/` に逐次書き込まれ、ラボ画面の `Codex依頼案` パネルにも実装状況として表示されます。
watcherのコードを更新した後は、起動中のwatcherを `Ctrl+C` で止めてから起動し直してください。

OpenAI APIは会話や依頼案の整理に使い、実ファイル編集・テスト・修正はCodex側で行う想定です。
Webサーバー自身は、安全のため任意コマンド実行やGit操作を行いません。

## 既存シミュレーション小改造

保存済みのCodex依頼案をもとに、既存シミュレーションの見た目変更だけを確認付きで限定適用できます。

できること:

- `プレビュー`: 依頼案から適用可能な変更、対象ファイル、注意点を確認する
- `適用`: `gravity_ball`, `maze_agent`, `flocking` の `customization.json` を更新し、`result.json` を再生成する
- 適用履歴を `logs/codex_tasks/events.jsonl` に保存する

限定適用できる変更:

- `gravity_ball`: ボール色、床色、軌跡色
- `maze_agent`: 壁色、床色、経路色、スタート色、ゴール色、エージェント色。壁色の既定値は黒 (`#000000`)
- `flocking`: 個体色パレット、境界線色

色は `#RRGGBB` または `赤`, `青`, `緑`, `黄色`, `red`, `blue` などの基本色名から判定します。
判定できない依頼、新規シミュレーション作成、Python/JavaScriptの自由編集、任意コマンド実行、Git操作は行いません。

## 初期状態に戻す

3D画面の左下にある `初期状態` ボタンを押すと、次を既定値に戻します。

- `gravity_ball`, `maze_agent`, `flocking` の `customization.json`
- 各シミュレーションの最新 `result.json`
- 画面上のシミュレーション選択、入力パラメータ、再生速度、視点、チャット表示、Codex依頼案パネル

会話ログやCodex依頼案ログは削除しません。
また、この機能は安全のため、ソースコードの自動復元、Git操作、任意コマンド実行は行いません。

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

Codex依頼案の詳細:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/codex-tasks/<task_id>"
```

Codex実装待ちへの登録:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/codex-tasks/<task_id>/request-implementation
```

Codex実装待ち一覧:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/codex-implementation-requests?status=pending"
```

限定適用プレビュー:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/codex-tasks/<task_id>/plan `
  -ContentType "application/json; charset=utf-8" `
  -Body '{"session_id":"demo"}'
```

限定適用:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/codex-tasks/<task_id>/apply `
  -ContentType "application/json; charset=utf-8" `
  -Body '{"confirm":true}'
```

初期状態へのリセット:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/lab/reset
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
logs/codex_tasks/events.jsonl
logs/codex_tasks/implementation_requests.jsonl
logs/codex_tasks/pending_implementation/
logs/codex_tasks/watcher_state.json
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
    current_datetime.js
    lab_ui.js
    main.js
    simulation_viewer.js
tools/
  codex_task_watcher.py
simulations/
  gravity_ball/
    config.json
    customization.json
    sim.py
    result.json
    README.md
  maze_agent/
    config.json
    customization.json
    sim.py
    result.json
    README.md
  flocking/
    config.json
    customization.json
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
