import os
import sys
from pathlib import Path

# Set env vars BEFORE any app imports
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SCHEDULER_ENABLED", "false")

# Ensure project root is importable when running tests without installation
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from app.main import app

def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["db"] in {"ok", "error"}
    assert isinstance(data["scheduler"], dict)
    # Scheduler enabled state depends on env; just verify it's present
    assert "scheduler_enabled" in data["scheduler"]