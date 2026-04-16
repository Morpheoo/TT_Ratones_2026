import argparse
import ctypes
import os
import signal
import subprocess
import sys
from typing import TextIO


ACTIVE_CHILD = None
ACTIVE_LOG = None


def set_console_title(title: str):
    if os.name != "nt" or not title:
        return
    try:
        ctypes.windll.kernel32.SetConsoleTitleW(str(title))
    except Exception:
        pass


def emit(message: str, log_handle: TextIO | None = None):
    print(message, flush=True)
    if log_handle:
        log_handle.write(message + "\n")
        log_handle.flush()


def terminate_child_tree():
    global ACTIVE_CHILD
    child = ACTIVE_CHILD
    if child is None or child.poll() is not None:
        return

    if os.name == "nt":
        try:
            child.send_signal(signal.CTRL_BREAK_EVENT)
            child.wait(timeout=5)
            return
        except Exception:
            pass
        subprocess.run(
            ["taskkill", "/PID", str(child.pid), "/T", "/F"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return

    try:
        child.terminate()
        child.wait(timeout=5)
    except Exception:
        child.kill()


def register_signal_handlers(log_handle: TextIO):
    def handler(_signum, _frame):
        emit("[STEP] CANCELLED", log_handle)
        emit("[INFO] Cancellation requested from console.", log_handle)
        terminate_child_tree()
        raise SystemExit(130)

    for sig_name in ["SIGINT", "SIGTERM", "SIGBREAK"]:
        sig = getattr(signal, sig_name, None)
        if sig is not None:
            try:
                signal.signal(sig, handler)
            except Exception:
                pass


def normalize_command(command: list[str]) -> list[str]:
    if command and command[0] == "--":
        return command[1:]
    return command


def main():
    parser = argparse.ArgumentParser(description="Run a child command and tee logs to console + file.")
    parser.add_argument("--log", required=True, help="Absolute path of the log file to write.")
    parser.add_argument("--label", default="Proceso TT 2026", help="Console title label.")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to execute after --")
    args = parser.parse_args()

    command = normalize_command(args.command)
    if not command:
        raise SystemExit("No child command was provided to run_with_live_log.py")

    log_path = os.path.abspath(args.log)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    set_console_title(args.label)

    global ACTIVE_CHILD, ACTIVE_LOG
    with open(log_path, "w", encoding="utf-8", buffering=1) as log_handle:
        ACTIVE_LOG = log_handle
        register_signal_handlers(log_handle)
        emit("=" * 72, log_handle)
        emit(f"[WRAPPER] Launching: {' '.join(command)}", log_handle)
        emit("=" * 72, log_handle)

        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

        ACTIVE_CHILD = subprocess.Popen(
            command,
            cwd=os.getcwd(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=creationflags,
        )

        return_code = 0
        try:
            assert ACTIVE_CHILD.stdout is not None
            for line in ACTIVE_CHILD.stdout:
                emit(line.rstrip("\r\n"), log_handle)
            return_code = ACTIVE_CHILD.wait()
        except KeyboardInterrupt:
            emit("[STEP] CANCELLED", log_handle)
            emit("[INFO] Cancellation requested from console.", log_handle)
            terminate_child_tree()
            return_code = 130
        finally:
            emit(f"[WRAPPER] Child exit code: {return_code}", log_handle)
            ACTIVE_CHILD = None
            ACTIVE_LOG = None

    raise SystemExit(return_code)


if __name__ == "__main__":
    main()
