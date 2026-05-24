from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path.cwd() / ".cache" / "matplotlib"))

from .pipeline import run_screening


def main() -> None:
    md_path, csv_path = run_screening()
    print(f"Markdown report: {md_path}")
    print(f"CSV output: {csv_path}")


if __name__ == "__main__":
    main()
