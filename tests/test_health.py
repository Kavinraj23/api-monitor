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