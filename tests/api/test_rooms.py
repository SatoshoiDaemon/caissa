def register(client, username="alice"):
    response = client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "correct horse battery staple"},
    )
    assert response.status_code == 201
    return response.get_json()


def test_public_room_requires_account(client):
    response = client.post("/api/v1/rooms", json={"name": "Public Room"})
    assert response.status_code == 401


def test_authenticated_room_creation_and_listing(client):
    register(client)
    response = client.post(
        "/api/v1/rooms",
        json={
            "name": "Friday Blitz",
            "access_mode": "public",
            "mode": "blitz",
            "initial_time_seconds": 300,
            "increment_seconds": 0,
        },
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["room"]["name"] == "Friday Blitz"
    assert data["room"]["spectator_count"] == 0
    assert data["room"]["clock"]["white_time_remaining_ms"] == 300000

    listed = client.get("/api/v1/rooms")
    assert listed.status_code == 200
    assert listed.get_json()["rooms"][0]["room_code"] == data["room_code"]


def test_code_only_room_is_not_publicly_listed_and_can_be_spectated_only_when_public(client):
    register(client)
    response = client.post(
        "/api/v1/rooms", json={"name": "Private Room", "access_mode": "code_only"}
    )
    assert response.status_code == 201
    room_code = response.get_json()["room_code"]
    assert client.get("/api/v1/rooms").get_json()["rooms"] == []
    assert client.post(f"/api/v1/rooms/{room_code}/spectate").status_code == 403


def test_public_room_issues_read_only_spectator_token(client):
    register(client)
    created = client.post("/api/v1/rooms", json={"name": "Watch Me"}).get_json()
    response = client.post(f"/api/v1/rooms/{created['room_code']}/spectate")
    assert response.status_code == 200
    data = response.get_json()
    assert data["spectator_token"]
    assert data["room"]["spectator_count"] == 1


def test_room_clock_comes_from_server_mode_preset(client):
    register(client)
    response = client.post(
        "/api/v1/rooms",
        json={"name": "Bullet Arena", "mode": "bullet", "initial_time_seconds": 1800},
    )
    assert response.status_code == 201
    assert response.get_json()["room"]["clock"]["white_time_remaining_ms"] == 60000
