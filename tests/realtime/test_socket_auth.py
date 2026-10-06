from backend.app.extensions import socketio


def test_socket_rejects_invalid_room_payload(app, client):
    socket_client = socketio.test_client(app)
    result = socket_client.emit(
        "join_room",
        {"game_id": "invalid", "room_code": "ABCDEFGH", "player_token": "x"},
        callback=True,
    )
    assert result["ok"] is False
    assert result["error"]


def test_two_socket_clients_share_authoritative_state(app, client):
    game_response = client.post("/api/v1/games", json={"player_name": "Alice"})
    game = game_response.get_json()
    black_response = client.post(
        f"/api/v1/rooms/{game['room_code']}/join", json={"player_name": "Bob"}
    )
    black = black_response.get_json()

    white_socket = socketio.test_client(app)
    black_socket = socketio.test_client(app)
    white_join = white_socket.emit(
        "join_room",
        {
            "game_id": game["game_id"],
            "room_code": game["room_code"],
            "player_token": game["player_token"],
        },
        callback=True,
    )
    black_join = black_socket.emit(
        "join_room",
        {
            "game_id": game["game_id"],
            "room_code": game["room_code"],
            "player_token": black["player_token"],
        },
        callback=True,
    )

    assert white_join["ok"] is True
    assert black_join["ok"] is True

    move_result = white_socket.emit(
        "make_move",
        {
            "game_id": game["game_id"],
            "room_code": game["room_code"],
            "player_token": game["player_token"],
            "move": {"from": "e2", "to": "e4"},
        },
        callback=True,
    )

    assert move_result["ok"] is True
    assert move_result["game_state"]["fen"].endswith(" b KQkq e3 0 1")
    assert move_result["game_state"]["version"] == 1
    restored = client.get(f"/api/v1/games/{game['game_id']}").get_json()
    assert restored["fen"] == move_result["game_state"]["fen"]
    assert white_socket.is_connected()
    assert black_socket.is_connected()


def test_socket_rejects_player_using_wrong_room(app, client):
    game = client.post("/api/v1/games", json={"player_name": "Alice"}).get_json()
    socket_client = socketio.test_client(app)

    result = socket_client.emit(
        "join_room",
        {
            "game_id": game["game_id"],
            "room_code": "ZZZZZZZZ",
            "player_token": game["player_token"],
        },
        callback=True,
    )

    assert result["ok"] is False
    assert result["error"] == "room and game do not match"


def test_spectator_receives_state_but_cannot_mutate(app, client):
    client.post(
        "/api/v1/auth/register",
        json={"username": "creator", "password": "correct horse battery staple"},
    )
    created = client.post("/api/v1/rooms", json={"name": "Spectator Test"}).get_json()
    spectator = client.post(f"/api/v1/rooms/{created['room_code']}/spectate").get_json()
    socket_client = socketio.test_client(app)
    result = socket_client.emit(
        "spectate_room",
        {"room_code": created["room_code"], "spectator_token": spectator["spectator_token"]},
        callback=True,
    )
    assert result["ok"] is True
    mutation = socket_client.emit(
        "make_move",
        {
            "game_id": created["game_id"],
            "room_code": created["room_code"],
            "player_token": spectator["spectator_token"],
            "move": {"from": "e2", "to": "e4"},
        },
        callback=True,
    )
    assert mutation["ok"] is False
    assert mutation["error"] == "spectators have read-only access"


def test_player_disconnects_and_reconnects_within_grace_window(app, client):
    game = client.post("/api/v1/games", json={"player_name": "Alice"}).get_json()
    socket_client = socketio.test_client(app)
    joined = socket_client.emit(
        "join_room",
        {
            "game_id": game["game_id"],
            "room_code": game["room_code"],
            "player_token": game["player_token"],
        },
        callback=True,
    )
    assert joined["ok"] is True
    socket_client.disconnect()
    reconnecting = socketio.test_client(app)
    result = reconnecting.emit(
        "join_room",
        {
            "game_id": game["game_id"],
            "room_code": game["room_code"],
            "player_token": game["player_token"],
        },
        callback=True,
    )
    assert result["ok"] is True
    restored = client.get(f"/api/v1/games/{game['game_id']}").get_json()
    assert restored["white_connected"] is True
