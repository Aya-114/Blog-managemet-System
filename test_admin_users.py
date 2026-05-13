from tests.conftest import auth_headers, login, register


def test_admin_can_manage_users(client):
    admin_response = register(client, "admin_user", role="admin")
    member_response = register(client, "member_user", role="author")
    admin_token, admin = login(client, "admin_user")

    users = client.get("/api/v1/admin/users", headers=auth_headers(admin_token))
    assert users.status_code == 200
    assert {user["username"] for user in users.json()} == {"admin_user", "member_user"}

    updated = client.put(
        f"/api/v1/admin/users/{member_response.json()['id']}",
        json={"username": "renamed_member", "role": "reader", "password": "newpass123"},
        headers=auth_headers(admin_token),
    )
    assert updated.status_code == 200
    assert updated.json()["username"] == "renamed_member"
    assert updated.json()["role"] == "reader"

    renamed_token, renamed_user = login(client, "renamed_member", password="newpass123")
    assert renamed_user["role"] == "reader"

    forbidden = client.get("/api/v1/admin/users", headers=auth_headers(renamed_token))
    assert forbidden.status_code == 403

    demote_self = client.put(
        f"/api/v1/admin/users/{admin['id']}",
        json={"role": "author"},
        headers=auth_headers(admin_token),
    )
    assert demote_self.status_code == 400

    delete_self = client.delete(f"/api/v1/admin/users/{admin['id']}", headers=auth_headers(admin_token))
    assert delete_self.status_code == 400

    deleted = client.delete(
        f"/api/v1/admin/users/{member_response.json()['id']}",
        headers=auth_headers(admin_token),
    )
    assert deleted.status_code == 204

    after_delete = client.get("/api/v1/admin/users", headers=auth_headers(admin_token))
    assert {user["username"] for user in after_delete.json()} == {"admin_user"}


def test_admin_user_update_rejects_duplicate_username(client):
    register(client, "admin_user", role="admin")
    first = register(client, "first_user", role="author")
    register(client, "second_user", role="reader")
    admin_token, _ = login(client, "admin_user")

    response = client.put(
        f"/api/v1/admin/users/{first.json()['id']}",
        json={"username": "second_user"},
        headers=auth_headers(admin_token),
    )
    assert response.status_code == 409


def test_admin_user_update_rejects_same_values(client):
    register(client, "admin_user", role="admin")
    member = register(client, "member_user", role="author", password="password123")
    admin_token, _ = login(client, "admin_user")

    response = client.put(
        f"/api/v1/admin/users/{member.json()['id']}",
        json={"username": "member_user", "password": "password123", "role": "author"},
        headers=auth_headers(admin_token),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "No changes provided"
