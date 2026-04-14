"""
Starts both Nexus services together:
  - FastAPI backend  (uvicorn, port 8000)
  - Telegram bot     (long polling)

Usage: uv run python run.py
"""

import subprocess
import sys
import os


def main() -> None:
    env = os.environ.copy()

    procs = [
        subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app",
             "--host", "127.0.0.1", "--port", "8000", "--reload"],
            env=env,
        ),
        subprocess.Popen(
            [sys.executable, "tg_bot.py"],
            env=env,
        ),
    ]

    print("Nexus running — FastAPI on :8000 | Telegram bot polling")
    print("Ctrl+C to stop both.\n")

    try:
        for p in procs:
            p.wait()
    except KeyboardInterrupt:
        print("\nShutting down…")
        for p in procs:
            p.terminate()
        for p in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()


if __name__ == "__main__":
    main()
