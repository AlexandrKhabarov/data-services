def test_health_ok(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "telegram_pool" in data
    pool = data["telegram_pool"]
    assert pool["total"] == 0
    assert pool["free"] == 0
    assert pool["busy"] == 0
