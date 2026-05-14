from tests.conftest import auth_headers, login, register


def prepare_post(client):
    register(client, "admin_user", role="admin")
    register(client, "author_user", role="author")
    register(client, "reader_user", role="reader")
    admin_token, _ = login(client, "admin_user")
    author_token, _ = login(client, "author_user")
    reader_token, _ = login(client, "reader_user")
    post = client.post(
        "/api/v1/posts",
        json={"title": "Nested comments", "content": "Comment thread demo"},
        headers=auth_headers(author_token),
    ).json()
    return post["id"], admin_token, author_token, reader_token


def test_nested_comments_and_comment_crud(client):
    post_id, admin_token, author_token, reader_token = prepare_post(client)

    top = client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "Top-level comment"},
        headers=auth_headers(reader_token),
    )
    assert top.status_code == 201
    top_id = top.json()["id"]

    reply = client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "Nested reply", "parent_id": top_id},
        headers=auth_headers(author_token),
    )
    assert reply.status_code == 201

    comments = client.get(f"/api/v1/posts/{post_id}/comments?skip=0&limit=10", headers=auth_headers(reader_token))
    assert comments.status_code == 200
    assert comments.json()[0]["children"][0]["content"] == "Nested reply"

    denied = client.put(
        f"/api/v1/comments/{top_id}",
        json={"content": "Wrong owner"},
        headers=auth_headers(author_token),
    )
    assert denied.status_code == 403

    edited = client.put(
        f"/api/v1/comments/{top_id}",
        json={"content": "Edited by commenter"},
        headers=auth_headers(reader_token),
    )
    assert edited.status_code == 200
    assert edited.json()["content"] == "Edited by commenter"

    deleted = client.delete(f"/api/v1/comments/{top_id}", headers=auth_headers(admin_token))
    assert deleted.status_code == 204


def test_parent_comment_must_belong_to_same_post(client):
    post_id, _, author_token, reader_token = prepare_post(client)
    second_post = client.post(
        "/api/v1/posts",
        json={"title": "Another post", "content": "Separate thread"},
        headers=auth_headers(author_token),
    ).json()
    other_comment = client.post(
        f"/api/v1/posts/{second_post['id']}/comments",
        json={"content": "Other post comment"},
        headers=auth_headers(reader_token),
    ).json()

    response = client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "Invalid parent", "parent_id": other_comment["id"]},
        headers=auth_headers(reader_token),
    )
    assert response.status_code == 400
