"""Allow both the pytest entry point and python -m pytest from the checkout."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
