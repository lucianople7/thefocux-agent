"""THE FOCUX Agent — ``python -m focux`` entry point."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from focux import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
