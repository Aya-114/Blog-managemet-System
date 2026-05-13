from tests.conftest import auth_headers, login, register


def test_cache_hits_and_admin_monitoring(client):
    register(client, "admin_user", role="admin")
    register(client, "author_user", role="author")
    admin_token, _ = login(client, "admin_user")
    author_token, _ = login(client, "author_user")

    client.post(
        "/api/v1/posts",
        json={"title": "Caching article", "content": "Cache-aside pattern"},
        headers=auth_headers(author_token),
    )

    first = client.get("/api/v1/posts?skip=0&limit=10", headers=auth_headers(admin_token))
    second = client.get("/api/v1/posts?skip=0&limit=10", headers=auth_headers(admin_token))
    assert first.status_code == 200
    assert second.status_code == 200

    health = client.get("/api/v1/monitoring/health")
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"

    metrics = client.get("/api/v1/monitoring/metrics", headers=auth_headers(admin_token))
    assert metrics.status_code == 200
    assert metrics.json()["cache"]["hits"] >= 1
    assert metrics.json()["total_requests"] >= 3

    logs = client.get("/api/v1/monitoring/logs", headers=auth_headers(admin_token))
    assert logs.status_code == 200
    assert "logs" in logs.json()


def test_reader_cannot_view_admin_metrics(client):
    register(client, "admin_user", role="admin")
    register(client, "reader_user", role="reader")
    reader_token, _ = login(client, "reader_user")

    response = client.get("/api/v1/monitoring/metrics", headers=auth_headers(reader_token))
    assert response.status_code == 403
