def create_online_game(client, name="Alice"):
    response = client.post("/api/v1/games", json={"player_name": name})
    assert response.status_code == 201
    return response.get_json()


def test_create_game_returns_token_and_state(client):
    data = create_online_game(client)
    assert data["player_color"] == "white"
    assert data["player_token"]
    assert data["room_code"]
    assert data["game_state"]["status"] == "active"


def test_invalid_input_is_rejected(client):
    assert client.post("/api/v1/games", json={"player_name": ""}).status_code == 400
    assert client.post("/api/v1/games", json={"player_name": "x" * 33}).status_code == 400


def test_move_requires_valid_token(client):
    game = create_online_game(client)
    url = f"/api/v1/games/{game['game_id']}/moves"
    assert client.post(url, json={"from": "e2", "to": "e4"}).status_code == 401
    assert (
        client.post(
            url, headers={"Authorization": "Bearer wrong"}, json={"from": "e2", "to": "e4"}
        ).status_code
        == 401
    )


def test_authorized_move_and_finished_game(client):
    game = client.post(
        "/api/v1/games", json={"player_name": "Alice", "mode": "local", "black_player": "Bob"}
    ).get_json()
    url = f"/api/v1/games/{game['game_id']}/moves"
    headers = {"Authorization": f"Bearer {game['player_token']}"}
    response = client.post(url, headers=headers, json={"from": "e2", "to": "e4"})
    assert response.status_code == 200

    resign = client.post(f"/api/v1/games/{game['game_id']}/resign", headers=headers)
    assert resign.status_code == 200
    assert client.post(url, headers=headers, json={"from": "e7", "to": "e5"}).status_code == 409


def test_server_clock_uses_persisted_fields_and_rejects_expired_move(client, repositories):
    game = create_online_game(client)
    joined = client.post(
        f"/api/v1/rooms/{game['room_code']}/join", json={"player_name": "Bob"}
    ).get_json()
    document = repositories[0].documents[game["game_id"]]
    from datetime import datetime, timedelta, timezone

    document["white_time_remaining_ms"] = 1
    document["clock"]["white_time_remaining_ms"] = 1
    document["clock_started_at"] = datetime.now(timezone.utc) - timedelta(seconds=2)
    document["clock"]["clock_started_at"] = document["clock_started_at"]
    document["active_clock_color"] = "white"
    document["clock"]["active_clock_color"] = "white"
    response = client.post(
        f"/api/v1/games/{game['game_id']}/moves",
        headers={"Authorization": f"Bearer {game['player_token']}"},
        json={"from": "e2", "to": "e4", "event_id": "timeout-move"},
    )
    assert response.status_code == 409
    assert repositories[0].documents[game["game_id"]]["status"] == "timeout"
    assert joined["game_state"]["white_time_remaining_ms"] > 0


def test_room_allows_one_black_player_only(client):
    game = create_online_game(client)
    join_url = f"/api/v1/rooms/{game['room_code']}/join"
    first = client.post(join_url, json={"player_name": "Bob"})
    second = client.post(join_url, json={"player_name": "Carol"})
    assert first.status_code == 200
    assert second.status_code == 409


def test_room_reconnects_existing_player_without_creating_a_duplicate(client):
    game = create_online_game(client)
    join_url = f"/api/v1/rooms/{game['room_code']}/join"
    joined = client.post(join_url, json={"player_name": "Bob"}).get_json()

    reconnect = client.post(
        join_url,
        headers={"Authorization": f"Bearer {joined['player_token']}"},
        json={},
    )

    assert reconnect.status_code == 200
    assert reconnect.get_json()["player_token"] == joined["player_token"]
    assert reconnect.get_json()["player_color"] == "black"


def test_reconnect_endpoint_restores_persisted_state(client):
    game = create_online_game(client)
    response = client.post(
        f"/api/v1/games/{game['game_id']}/reconnect",
        headers={"Authorization": f"Bearer {game['player_token']}"},
    )

    assert response.status_code == 200
    assert response.get_json()["fen"].endswith(" 0 1")
    assert response.get_json()["player_color"] == "white"


def test_invalid_position_and_promotion_are_bad_requests(client):
    game = create_online_game(client)
    game_url = f"/api/v1/games/{game['game_id']}"
    assert client.get(f"{game_url}/moves/not-a-square").status_code == 400
    headers = {"Authorization": f"Bearer {game['player_token']}"}
    response = client.post(
        f"{game_url}/moves",
        headers=headers,
        json={"from": "e2", "to": "e4", "promotion": "k"},
    )
    assert response.status_code == 400


def test_draw_offer_decline_and_accept_are_authorized(client):
    game = create_online_game(client)
    black = client.post(
        f"/api/v1/rooms/{game['room_code']}/join", json={"player_name": "Bob"}
    ).get_json()
    white_headers = {"Authorization": f"Bearer {game['player_token']}"}
    black_headers = {"Authorization": f"Bearer {black['player_token']}"}

    offered = client.post(
        f"/api/v1/games/{game['game_id']}/draw/offer",
        headers=white_headers,
        json={"event_id": "draw-offer-1"},
    )
    assert offered.status_code == 200
    assert offered.get_json()["draw_offer"]["offered_by"] == "white"
    assert (
        client.post(
            f"/api/v1/games/{game['game_id']}/draw/offer",
            headers=white_headers,
            json={"event_id": "draw-offer-2"},
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/v1/games/{game['game_id']}/draw/decline",
            headers=black_headers,
            json={"event_id": "draw-decline-1"},
        ).status_code
        == 200
    )

    client.post(
        f"/api/v1/games/{game['game_id']}/draw/offer",
        headers=white_headers,
        json={"event_id": "draw-offer-3"},
    )
    accepted = client.post(
        f"/api/v1/games/{game['game_id']}/draw/accept",
        headers=black_headers,
        json={"event_id": "draw-accept-1"},
    )
    assert accepted.status_code == 200
    assert accepted.get_json()["status"] == "draw"
    assert (
        client.post(
            f"/api/v1/games/{game['game_id']}/draw/accept",
            headers=black_headers,
            json={"event_id": "draw-accept-1"},
        ).get_json()["status"]
        == "draw"
    )


def test_resignation_is_idempotent_after_game_ends(client):
    game = create_online_game(client)
    headers = {"Authorization": f"Bearer {game['player_token']}"}
    first = client.post(
        f"/api/v1/games/{game['game_id']}/resign",
        headers=headers,
        json={"event_id": "resign-1"},
    )
    second = client.post(
        f"/api/v1/games/{game['game_id']}/resign",
        headers=headers,
        json={"event_id": "resign-1"},
    )
    assert first.status_code == second.status_code == 200
    assert first.get_json()["status"] == second.get_json()["status"] == "resignation"
