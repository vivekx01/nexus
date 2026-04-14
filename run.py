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

    host = os.environ.get("HOST", "127.0.0.1")
    port = os.environ.get("PORT", "8000")

    uvicorn_cmd = [
        sys.executable, "-m", "uvicorn", "app.main:app",
        "--host", host,
        "--port", port,
    ]
    if os.environ.get("RELOAD", "false").lower() == "true":
        uvicorn_cmd.append("--reload")

    procs = [
        subprocess.Popen(uvicorn_cmd, env=env),
        subprocess.Popen([sys.executable, "tg_bot.py"], env=env),
    ]

    print(f"Nexus running — FastAPI on {host}:{port} | Telegram bot polling")
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
