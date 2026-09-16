"""Backward-compatible launcher for local checkouts."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from skalspeech.cli import app

if __name__ == "__main__":
    app()