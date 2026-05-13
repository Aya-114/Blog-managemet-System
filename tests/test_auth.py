from tests.conftest import auth_headers, login, register


def test_register_login_and_me(client):
    response = register(client, "admin_user", role="admin")
    assert response.status_code == 201
    assert response.json()["role"] == "admin"

    duplicate = register(client, "admin_user", role="reader")
    assert duplicate.status_code == 409

    token, user = login(client, "admin_user")
    assert user["username"] == "admin_user"

    me = client.get("/api/v1/auth/me", headers=auth_headers(token))
    assert me.status_code == 200
    assert me.json()["role"] == "admin"


def test_only_first_user_can_self_register_as_admin(client):
    assert register(client, "first_author", role="author").status_code == 201
    response = register(client, "late_admin", role="admin")
    assert response.status_code == 403


def test_invalid_token_is_rejected(client):
    response = client.get("/api/v1/auth/me", headers=auth_headers("bad.token.value"))
    assert response.status_code == 401
