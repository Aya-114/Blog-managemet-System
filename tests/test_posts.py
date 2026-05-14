from tests.conftest import auth_headers, login, register


def setup_users(client):
    register(client, "admin_user", role="admin")
    register(client, "author_user", role="author")
    register(client, "reader_user", role="reader")
    admin_token, _ = login(client, "admin_user")
    author_token, author = login(client, "author_user")
    reader_token, _ = login(client, "reader_user")
    return admin_token, author_token, reader_token, author


def test_post_crud_permissions_and_pagination(client):
    admin_token, author_token, reader_token, author = setup_users(client)

    forbidden = client.post(
        "/api/v1/posts",
        json={"title": "Reader post", "content": "Nope"},
        headers=auth_headers(reader_token),
    )
    assert forbidden.status_code == 403

    created = client.post(
        "/api/v1/posts",
        json={"title": "First Blog Post", "content": "A useful article"},
        headers=auth_headers(author_token),
    )
    assert created.status_code == 201
    post_id = created.json()["id"]
    assert created.json()["owner_id"] == author["id"]

    listing = client.get("/api/v1/posts?skip=0&limit=5&search=blog", headers=auth_headers(reader_token))
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    denied_update = client.put(
        f"/api/v1/posts/{post_id}",
        json={"title": "Reader edit"},
        headers=auth_headers(reader_token),
    )
    assert denied_update.status_code == 403

    updated = client.put(
        f"/api/v1/posts/{post_id}",
        json={"content": "Updated by author"},
        headers=auth_headers(author_token),
    )
    assert updated.status_code == 200
    assert updated.json()["content"] == "Updated by author"

    deleted = client.delete(f"/api/v1/posts/{post_id}", headers=auth_headers(admin_token))
    assert deleted.status_code == 204

    missing = client.get(f"/api/v1/posts/{post_id}", headers=auth_headers(reader_token))
    assert missing.status_code == 404


def test_unauthorized_post_access_is_blocked(client):
    response = client.get("/api/v1/posts")
    assert response.status_code == 401
