from __future__ import annotations

import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from app.config import DECISION_RECORDS_PATH


def main() -> int:
    records_path = Path(DECISION_RECORDS_PATH)
    records_path.parent.mkdir(parents=True, exist_ok=True)
    records_path.write_text("[]\n", encoding="utf-8")
    print(f"Reset decision records: {records_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
