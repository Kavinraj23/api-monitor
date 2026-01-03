import os
import sys
from pathlib import Path

# Make project root importable for all tests
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Default test env (can be overridden per-test)
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SCHEDULER_ENABLED", "false")
