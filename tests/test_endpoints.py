import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "AetherIntel Engine"}

def test_stream_validation_error():
    # Empty query must fail with 400
    response = client.post("/api/v1/research/stream", json={"research_query": "", "thread_id": "test_t"})
    assert response.status_code == 400
    assert "cannot be empty" in response.json()["detail"]

def test_approve_no_active_interrupt():
    # Try approving a session that doesn't exist
    response = client.post("/api/v1/research/approve", json={
        "thread_id": "non_existent_thread_id_abc",
        "approved": True
    })
    assert response.status_code == 400
    assert "No active graph execution" in response.json()["detail"]
