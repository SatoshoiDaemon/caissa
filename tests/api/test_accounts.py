def register(client, username="alice", password="correct horse battery"):
    response = client.post(
        "/api/v1/auth/register", json={"username": username, "password": password}
    )
    assert response.status_code == 201
    return response.get_json()


def test_register_uses_cookie_and_returns_recovery_codes_once(client):
    data = register(client)
    assert len(data["recovery_codes"]) == 6
    assert data["user"]["username"] == "alice"
    assert client.get_cookie("caissa_session") is not None
    assert client.get("/api/v1/auth/me").get_json()["user"]["username"] == "alice"


def test_login_logout_and_profile_update(client):
    register(client)
    client.post("/api/v1/auth/logout")
    assert client.get("/api/v1/auth/me").status_code == 401
    login = client.post(
        "/api/v1/auth/login", json={"username": "ALICE", "password": "correct horse battery"}
    )
    assert login.status_code == 200
    profile = client.patch(
        "/api/v1/users/me/profile",
        json={
            "bio": "A local chess player",
            "status_emoji": "🙂",
            "status_message": "Ready to play",
            "timezone": "America/Sao_Paulo",
        },
    )
    assert profile.status_code == 200
    public = client.get("/api/v1/users/alice").get_json()["user"]
    assert public["status"] == "🙂 Ready to play"
    assert public["timezone"] == "America/Sao_Paulo"


def test_recovery_code_is_one_time_and_revokes_sessions(client):
    data = register(client)
    code = data["recovery_codes"][0]
    client.post("/api/v1/auth/logout")
    recovered = client.post(
        "/api/v1/auth/recovery",
        json={"username": "alice", "recovery_code": code, "new_password": "new password 123"},
    )
    assert recovered.status_code == 200
    assert (
        client.post(
            "/api/v1/auth/recovery",
            json={"username": "alice", "recovery_code": code, "new_password": "another password"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/login", json={"username": "alice", "password": "new password 123"}
        ).status_code
        == 200
    )


def test_authenticated_players_are_linked_and_results_count_once(client):
    alice = register(client, "alice")
    alice_game = client.post("/api/v1/games", json={"player_name": "Alice"}).get_json()
    second_client = client.application.test_client()
    register(second_client, "bob")
    joined = second_client.post(
        f"/api/v1/rooms/{alice_game['room_code']}/join", json={"player_name": "Bob"}
    )
    assert joined.status_code == 200
    assert joined.get_json()["player_color"] == "black"

    assert (
        second_client.post(
            f"/api/v1/games/{alice_game['game_id']}/resign",
            headers={"Authorization": f"Bearer {joined.get_json()['player_token']}"},
        ).status_code
        == 200
    )
    stats = client.get("/api/v1/users/me/stats")
    assert stats.status_code == 200
    assert stats.get_json()["overall"]["wins"] == 1
    assert stats.get_json()["overall"]["total"] == 1
    assert client.get("/api/v1/users/me/games").get_json()["games"][0]["result"] == "win"
    assert alice["user"]["username"] == "alice"
