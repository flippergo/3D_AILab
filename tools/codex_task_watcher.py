from __future__ import annotations

import argparse
import atexit
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
PENDING_DIR = ROOT_DIR / "logs" / "codex_tasks" / "pending_implementation"
EVENT_LOG_PATH = ROOT_DIR / "logs" / "codex_tasks" / "events.jsonl"
STATE_PATH = ROOT_DIR / "logs" / "codex_tasks" / "watcher_state.json"
OUTPUT_DIR = ROOT_DIR / "logs" / "codex_tasks" / "watcher_outputs"
LOCK_PATH = ROOT_DIR / "logs" / "codex_tasks" / "watcher.lock"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Watch saved 3D-AI Lab Codex implementation requests and pass them to codex exec."
    )
    parser.add_argument("--once", action="store_true", help="Process pending requests once, then exit.")
    parser.add_argument("--poll-interval", type=float, default=3.0, help="Polling interval in seconds.")
    parser.add_argument("--codex-command", default="codex", help="Codex CLI command or absolute path.")
    parser.add_argument(
        "--sandbox",
        default="danger-full-access",
        choices=["read-only", "workspace-write", "danger-full-access"],
        help=(
            "Sandbox mode passed to codex exec. The default avoids the Windows "
            "workspace-write sandbox helper, which can fail during local automation."
        ),
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the codex command without running it.")
    args = parser.parse_args()

    if not acquire_lock():
        print("Another codex_task_watcher.py process is already running.", file=sys.stderr)
        return 3

    codex_command = resolve_codex_command(args.codex_command, validate=True)
    if not codex_command:
        print(f"Codex command was not found: {args.codex_command}", file=sys.stderr)
        print("Use --codex-command with the full path to codex.exe if Codex is installed in a custom location.", file=sys.stderr)
        return 2
    args.codex_command = codex_command

    print(f"Watching: {PENDING_DIR}")
    print(f"Codex command: {args.codex_command}")
    print("Press Ctrl+C to stop.")

    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    while True:
        processed_any = process_pending_requests(args)
        if args.once:
            return 0
        if not processed_any:
            time.sleep(args.poll_interval)


def resolve_codex_command(command: str, *, validate: bool) -> str | None:
    for candidate in iter_codex_command_candidates(command):
        if validate and not is_runnable_codex_command(candidate):
            continue
        return candidate
    return None


def iter_codex_command_candidates(command: str):
    seen: set[str] = set()

    def yield_once(candidate: str | None):
        if not candidate:
            return
        key = candidate.lower()
        if key in seen:
            return
        seen.add(key)
        yield candidate

    command_path = Path(command)
    if command_path.exists():
        yield from yield_once(str(command_path))

    yield from yield_once(shutil.which(command))

    if os.name == "nt":
        for candidate in find_all_with_where(command):
            yield from yield_once(candidate)
        yield from yield_once(find_with_powershell_get_command(command))
        yield from yield_once(find_standalone_codex())
        yield from yield_once(find_windowsapps_codex())


def is_runnable_codex_command(command: str) -> bool:
    try:
        completed = subprocess.run(
            [command, "--version"],
            capture_output=True,
            cwd=ROOT_DIR,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return completed.returncode == 0


def find_with_where(command: str) -> str | None:
    candidates = find_all_with_where(command)
    return candidates[0] if candidates else None


def find_all_with_where(command: str) -> list[str]:
    try:
        completed = subprocess.run(
            ["where.exe", command],
            capture_output=True,
            cwd=ROOT_DIR,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if completed.returncode != 0:
        return []

    candidates: list[str] = []
    for line in completed.stdout.splitlines():
        candidate = line.strip()
        if candidate and Path(candidate).exists():
            candidates.append(candidate)
    return candidates


def find_with_powershell_get_command(command: str) -> str | None:
    candidates = [command]
    if not command.lower().endswith(".exe"):
        candidates.append(f"{command}.exe")

    for candidate_command in candidates:
        try:
            completed = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-Command",
                    f"(Get-Command {candidate_command} -ErrorAction Stop).Source",
                ],
                capture_output=True,
                cwd=ROOT_DIR,
                encoding="utf-8",
                errors="replace",
                text=True,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            continue

        if completed.returncode != 0:
            continue

        for line in completed.stdout.splitlines():
            candidate = line.strip()
            if candidate and Path(candidate).exists():
                return candidate

    return None


def find_windowsapps_codex() -> str | None:
    windowsapps = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "WindowsApps"
    patterns = [
        "OpenAI.Codex_*\\app\\resources\\codex.exe",
        "OpenAI.Codex_*\\app\\resources\\codex",
    ]
    for pattern in patterns:
        for candidate in sorted(windowsapps.glob(pattern), reverse=True):
            if candidate.exists():
                return str(candidate)
    return None


def find_standalone_codex() -> str | None:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return None

    candidates = [
        Path(local_app_data) / "Programs" / "OpenAI" / "Codex" / "bin" / "codex.exe",
        Path(local_app_data) / "Programs" / "OpenAI" / "Codex" / "bin" / "codex.EXE",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    versioned_bin = Path(local_app_data) / "OpenAI" / "Codex" / "bin"
    for candidate in sorted(versioned_bin.glob("*\\codex.exe"), reverse=True):
        if candidate.exists():
            return str(candidate)
    return None


def process_pending_requests(args: argparse.Namespace) -> bool:
    state = load_state()
    processed_any = False

    for handoff_path in sorted(PENDING_DIR.glob("*.md"), key=lambda path: path.stat().st_mtime):
        key = str(handoff_path.relative_to(ROOT_DIR))
        status = state.get(key, {}).get("status")
        if status in {"in_progress", "completed"}:
            continue

        processed_any = True
        if args.dry_run:
            run_codex_for_handoff(
                handoff_path=handoff_path,
                codex_command=args.codex_command,
                sandbox=args.sandbox,
                dry_run=True,
            )
            continue

        mark_state(state, key, "in_progress", output_file=str(output_path_for_handoff(handoff_path).relative_to(ROOT_DIR)))
        append_event(
            {
                "event_type": "watcher_started",
                "handoff_file": key,
                "status": "in_progress",
            }
        )

        try:
            result = run_codex_for_handoff(
                handoff_path=handoff_path,
                codex_command=args.codex_command,
                sandbox=args.sandbox,
                dry_run=args.dry_run,
            )
        except Exception as error:
            result = {
                "exit_code": 1,
                "agent_failed": True,
                "error": f"watcher exception: {error}",
            }
        exit_code = result["exit_code"]
        final_status = "failed" if result.get("agent_failed") or exit_code != 0 else "completed"
        mark_state(
            state,
            key,
            final_status,
            exit_code=exit_code,
            error=result.get("error"),
            output_file=result.get("output_file"),
        )
        append_event(
            {
                "event_type": "watcher_completed",
                "handoff_file": key,
                "status": final_status,
                "exit_code": exit_code,
                "error": result.get("error"),
                "output_file": result.get("output_file"),
            }
        )

    return processed_any


def acquire_lock() -> bool:
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    if LOCK_PATH.exists():
        pid_text = LOCK_PATH.read_text(encoding="utf-8", errors="replace").strip()
        if pid_text.isdigit() and process_exists(int(pid_text)):
            return False
        LOCK_PATH.unlink(missing_ok=True)

    try:
        fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False

    with os.fdopen(fd, "w", encoding="utf-8") as fp:
        fp.write(str(os.getpid()))
    atexit.register(release_lock)
    return True


def release_lock() -> None:
    try:
        if LOCK_PATH.exists() and LOCK_PATH.read_text(encoding="utf-8", errors="replace").strip() == str(os.getpid()):
            LOCK_PATH.unlink()
    except OSError:
        pass


def process_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def run_codex_for_handoff(*, handoff_path: Path, codex_command: str, sandbox: str, dry_run: bool) -> dict[str, Any]:
    prompt = build_prompt(handoff_path)
    command = [
        codex_command,
        "exec",
        "--sandbox",
        sandbox,
        prompt,
    ]

    print(f"\n=== Codex implementation request: {handoff_path.name} ===")
    if dry_run:
        print(" ".join(command))
        return {"exit_code": 0}

    output_path = output_path_for_handoff(handoff_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined_chunks: list[str] = []
    try:
        with output_path.open("w", encoding="utf-8", errors="replace") as output_fp:
            output_fp.write(f"=== Codex implementation request: {handoff_path.name} ===\n")
            output_fp.write(f"Command: {' '.join(command[:4])} <prompt>\n\n")
            output_fp.flush()

            completed = subprocess.Popen(
                command,
                cwd=ROOT_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding="utf-8",
                errors="replace",
                text=True,
                bufsize=1,
            )

            assert completed.stdout is not None
            for line in completed.stdout:
                combined_chunks.append(line)
                output_fp.write(line)
                output_fp.flush()
                print(line, end="")

            exit_code = completed.wait()
    except PermissionError as error:
        print(f"Failed to start Codex: {error}", file=sys.stderr)
        print("Install the standalone Codex CLI, or pass a runnable CLI path with --codex-command.", file=sys.stderr)
        return {"exit_code": 126, "agent_failed": True, "error": str(error)}
    except OSError as error:
        print(f"Failed to start Codex: {error}", file=sys.stderr)
        return {"exit_code": 127, "agent_failed": True, "error": str(error)}

    combined_output = "".join(combined_chunks)
    agent_error = detect_agent_failure(combined_output)
    return {
        "exit_code": exit_code,
        "agent_failed": agent_error is not None,
        "error": agent_error,
        "output_file": str(output_path.relative_to(ROOT_DIR)),
    }


def output_path_for_handoff(handoff_path: Path) -> Path:
    return OUTPUT_DIR / f"{handoff_path.stem}.log"


def write_codex_output(handoff_path: Path, output: str) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = output_path_for_handoff(handoff_path)
    output_path.write_text(output, encoding="utf-8")
    return str(output_path.relative_to(ROOT_DIR))


def detect_agent_failure(output: str) -> str | None:
    failure_markers = [
        "実装は開始できませんでした",
        "変更・テストは行っていません",
        "sandbox helper 欠落",
        "orchestrator_helper_launch_failed",
        "task failed",
        "turn.failed",
    ]
    for marker in failure_markers:
        if marker in output:
            return marker
    return None


def build_prompt(handoff_path: Path) -> str:
    relative_path = handoff_path.relative_to(ROOT_DIR)
    return f"""3D-AI Labの未処理の実装依頼を実装してください。

依頼ファイル:
{relative_path}

作業手順:
1. 依頼ファイルを読み、対象範囲と制約を確認する。
2. 必要なソース変更、README更新、テストを行う。
3. 実行時ログや生成物を不要にコミット対象へ混ぜない。
4. ユーザが明示していない限り、git commit / git push は行わない。
5. 完了時に、変更内容と検証結果を簡潔に報告する。

この依頼は3D-AI Labのローカルwatcherから渡されています。
"""


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        backup_path = STATE_PATH.with_suffix(f".broken-{int(time.time())}.json")
        STATE_PATH.replace(backup_path)
        return {}


def mark_state(
    state: dict[str, Any],
    key: str,
    status: str,
    *,
    exit_code: int | None = None,
    error: str | None = None,
    output_file: str | None = None,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    current = state.get(key, {})
    current["status"] = status
    current["updated_at"] = now
    if "created_at" not in current:
        current["created_at"] = now
    if exit_code is not None:
        current["exit_code"] = exit_code
    elif "exit_code" in current:
        del current["exit_code"]
    if status in {"in_progress", "completed"} and "error" in current:
        del current["error"]
    if error:
        current["error"] = error
    if output_file:
        current["output_file"] = output_file
    state[key] = current
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_event(event: dict[str, Any]) -> None:
    payload = {
        "event_id": f"watcher_{int(time.time() * 1000)}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        **event,
    }
    EVENT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVENT_LOG_PATH.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(payload, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
