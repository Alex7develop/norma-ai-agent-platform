"""Backward-compatible entrypoint; prefer `python -m app.workers.main`."""

from app.workers.main import main

if __name__ == "__main__":
    main()
