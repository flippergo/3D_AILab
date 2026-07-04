# 3D-AI Lab

3D-AI Lab は、学生向けの小さなAI入門ツールです。
このMVPでは、ブラウザ上の3D空間、ラボ助手チャット、FastAPI連携、会話ログ保存に加えて、Phase 4〜5 の `gravity_ball` シミュレーションを実行・再生できます。

現時点ではAPIキーや外部LLMサービスは使いません。

## 実装済みの機能

- ブラウザ上に Three.js の3Dラボ空間を表示する
- 簡単なラボ助手アバターと吹き出しを表示する
- 学生の入力を Python/FastAPI バックエンドの `POST /chat` に送信する
- 会話ログを `logs/sessions/` に JSONL 形式で保存する
- APIキーなしのルールベース版ラボ助手が、学生の入力を実験案に分解する
- Codex向けタスク案を生成する
- `gravity_ball` を実行し、`result.json` を生成する
- 生成されたボールの落下・反発シミュレーションを3D空間で再生する
- マウス操作で3D視点を回転、ズーム、パンする
- 重力、初期高さ、反発係数をUIまたは簡単なチャット指示で変更する

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

`迷路をエージェントが学習しながら進む` のような未実装の題材は、現時点では実行しません。
代わりに、Phase 7以降で実装するための実験案とCodex向けタスク案を表示します。

Codex向けタスク案は生成するだけで、自動実装は行いません。
自動実装はPhase 6以降の範囲です。

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

## ログ

チャット内容は、次の形式で追記保存されます。

```text
logs/sessions/session_<session_id>.jsonl
```

シミュレーション実行ログは、次の形式で追記保存されます。

```text
logs/experiments/gravity_ball.jsonl
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
logs/
  sessions/
  experiments/
requirements.txt
```

## 今後のLLM連携

将来、実際のLLMと接続する場合は `backend/llm_client.py` を差し替えます。
`/chat` のAPI形状は保ち、`generate_reply()` の中身を実LLM呼び出しに置き換える想定です。
