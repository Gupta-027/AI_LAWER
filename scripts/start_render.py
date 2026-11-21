"""Start the existing Streamlit app on Render's assigned public-service port.

Keep launch configuration in code instead of shell-specific variable expansion.
Local development can continue to use `python -m streamlit run app.py`.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Mapping

ROOT = Path(__file__).resolve().parents[1]


def build_command(environment: Mapping[str, str] | None = None) -> list[str]:
    environment = os.environ if environment is None else environment
    raw_port = environment.get("PORT", "10000")
    try:
        port = int(raw_port)
    except (TypeError, ValueError) as exc:
        raise ValueError("PORT must be an integer from 1 to 65535") from exc
    if not 1 <= port <= 65535:
        raise ValueError("PORT must be an integer from 1 to 65535")
    return [
        sys.executable, "-m", "streamlit", "run", str(ROOT / "app.py"),
        "--server.address=0.0.0.0", f"--server.port={port}",
        "--server.headless=true", "--server.fileWatcherType=none",
        "--server.runOnSave=false", "--browser.gatherUsageStats=false",
        "--server.enableCORS=true", "--server.enableXsrfProtection=true",
    ]


def main() -> None:
    command = build_command()
    os.chdir(ROOT)
    # Replace this launcher on Linux so Render's termination signal reaches
    # Streamlit directly. Credentials never enter the command or output.
    os.execv(sys.executable, command)


if __name__ == "__main__":
    main()
