import json

from flask import request
from flask_socketio import disconnect, emit, join_room

from ..api.schemas import event_id as validate_event_id
from ..api.schemas import move_payload, room_code
from ..app.errors import ApiError
from ..infrastructure.rate_limiter import (
    RedisRateLimiter,
    claim_presence,
    release_presence,
)
from ..services.game_service import GameService
from ..services.room_service import RoomService
from .socket_auth import socket_credentials


def register_socket_events(socketio, app):
    def service():
        return GameService(
            app.extensions["game_repository"],
            app.extensions["room_repository"],
            app.extensions["redis_client"],
            app.extensions["user_repository"],
        )

    def publish_clock_ticks():
        while True:
            socketio.sleep(1)
            repository = app.extensions["game_repository"]
            if not hasattr(repository, "list_active"):
                continue
            for document in repository.list_active():
                try:
                    state = service().get_state(document["_id"])
                    room = app.extensions["room_repository"].find_by_game(document["_id"])
                    if room:
                        if state.get("status") in {"timeout", "abandonment"}:
                            socketio.emit(
                                "game_ended",
                                {
                                    "winner": state.get("winner"),
                                    "reason": state["status"],
                                    "game_state": state,
                                },
                                to=room["_id"],
                            )
                        socketio.emit(
                            "clock_updated",
                            {"game_id": document["_id"], "game_state": state},
                            to=room["_id"],
                        )
                except ApiError:
                    continue

    if not app.config.get("TESTING"):
        socketio.start_background_task(publish_clock_ticks)

    @socketio.on("join_room")
    def handle_join(data):
        try:
            game_id, code, token = socket_credentials(data)
            room = app.extensions["room_repository"].get(room_code(code))
            if not room or room["game_id"] != game_id:
                raise ApiError("room and game do not match", 403)
            game_service = service()
            player = game_service.authenticate(game_id, token)
            was_disconnected = bool(player.get("disconnected_at"))
            join_room(code)
            redis_client = app.extensions["redis_client"]
            previous_sid = claim_presence(redis_client, game_id, player["color"], request.sid)
            if previous_sid and previous_sid != request.sid:
                disconnect(previous_sid)
            redis_client.setex(
                f"presence:socket:{request.sid}",
                300,
                json.dumps({"game_id": game_id, "room_code": code, "color": player["color"]}),
            )
            game_service.set_presence(game_id, token, True, request.sid)
            state = game_service.get_state(game_id)
            emit(
                "room_joined",
                {"room_code": code, "player_color": player["color"], "game_state": state},
                to=request.sid,
            )
            emit("room_state", {"room_code": code, "game_state": state}, to=request.sid)
            if was_disconnected:
                emit("player_reconnected", {"player_color": player["color"]}, to=code)
            emit(
                "player_joined",
                {"player_name": player["name"], "player_color": player["color"]},
                to=code,
                include_self=False,
            )
        except ApiError as error:
            emit("server_error", {"error": error.message})
            return {"ok": False, "error": error.message}
        return {"ok": True}

    @socketio.on("spectate_room")
    def handle_spectate(data):
        try:
            if not isinstance(data, dict):
                raise ApiError("invalid event payload", 400)
            code = room_code(data.get("room_code"))
            token = data.get("spectator_token")
            if not isinstance(token, str) or not token:
                raise ApiError("spectator_token is required", 400)
            room = app.extensions["room_repository"].get(code)
            if not room:
                raise ApiError("room not found", 404)
            RoomService(
                app.extensions["room_repository"], app.extensions["game_repository"]
            ).authenticate_spectator(code, token)
            join_room(code)
            redis_client = app.extensions["redis_client"]
            redis_client.setex(
                f"presence:socket:{request.sid}",
                300,
                json.dumps(
                    {
                        "room_code": code,
                        "role": "spectator",
                        "spectator_token_hash": RoomService.hash_token(token),
                    }
                ),
            )
            state = service().get_state(room["game_id"])
            emit("room_state", {"room_code": code, "game_state": state}, to=request.sid)
            emit("spectator_joined", {"spectator_count": len(room.get("spectators", []))}, to=code)
            return {"ok": True, "room_code": code, "game_state": state}
        except ApiError as error:
            emit("server_error", {"error": error.message})
            return {"ok": False, "error": error.message}

    @socketio.on("make_move")
    def handle_move(data):
        try:
            if not isinstance(data, dict):
                raise ApiError("invalid event payload", 400)
            if not RedisRateLimiter(app.extensions["redis_client"]).allow(
                f"socket_move:{data.get('player_token', '')}", 60, 60
            ):
                raise ApiError("rate limit exceeded", 429)
            game_id, code, token = socket_credentials(data)
            socket_metadata = app.extensions["redis_client"].get(f"presence:socket:{request.sid}")
            if socket_metadata and json.loads(socket_metadata).get("role") == "spectator":
                raise ApiError("spectators have read-only access", 403)
            room = app.extensions["room_repository"].get(room_code(code))
            if not room or room["game_id"] != game_id:
                raise ApiError("room and game do not match", 403)
            from_pos, to_pos, promotion = move_payload(data.get("move", {}))
            state = service().make_move(
                game_id, token, from_pos, to_pos, promotion, validate_event_id(data.get("event_id"))
            )
            emit(
                "move_made",
                {
                    "move": {"from": from_pos, "to": to_pos, "promotion": promotion},
                    "game_state": state,
                },
                to=code,
            )
            emit("clock_updated", {"game_state": state}, to=code)
            return {"ok": True, "game_state": state}
        except (ApiError, TimeoutError) as error:
            emit("server_error", {"error": str(error)})
            return {"ok": False, "error": str(error)}

    @socketio.on("resign_game")
    def handle_resign(data):
        try:
            _reject_spectator()
            game_id, code, token = socket_credentials(data)
            result = service().finish(
                game_id, token, "resignation", event_id=validate_event_id(data.get("event_id"))
            )
            emit(
                "game_ended",
                {"winner": result["winner"], "reason": "resignation", "game_state": result},
                to=code,
            )
        except ApiError as error:
            emit("server_error", {"error": error.message})

    @socketio.on("offer_draw")
    def handle_offer_draw(data):
        try:
            _reject_spectator()
            game_id, code, token = socket_credentials(data)
            result = service().offer_draw(game_id, token, validate_event_id(data.get("event_id")))
            emit("draw_offered", {"game_state": result}, to=code, include_self=False)
        except ApiError as error:
            emit("server_error", {"error": error.message})

    @socketio.on("accept_draw")
    def handle_accept_draw(data):
        try:
            _reject_spectator()
            game_id, code, token = socket_credentials(data)
            result = service().finish(
                game_id, token, "draw", event_id=validate_event_id(data.get("event_id"))
            )
            emit("game_ended", {"winner": None, "reason": "draw", "game_state": result}, to=code)
        except ApiError as error:
            emit("server_error", {"error": error.message})

    @socketio.on("decline_draw")
    def handle_decline_draw(data):
        try:
            _reject_spectator()
            game_id, code, token = socket_credentials(data)
            result = service().decline_draw(game_id, token, validate_event_id(data.get("event_id")))
            emit("draw_declined", {"game_state": result}, to=code)
        except ApiError as error:
            emit("server_error", {"error": error.message})

    @socketio.on("disconnect")
    def handle_disconnect():
        redis_client = app.extensions["redis_client"]
        socket_key = f"presence:socket:{request.sid}"
        metadata = redis_client.get(socket_key) if hasattr(redis_client, "get") else None
        if metadata:
            details = json.loads(metadata)
            if details.get("role") != "spectator":
                release_presence(redis_client, details["game_id"], details["color"], request.sid)
                service().clear_presence(details["game_id"], details["color"], request.sid)
                emit(
                    "player_disconnected",
                    {"player_color": details["color"], "reconnect_grace_seconds": 60},
                    to=details["room_code"],
                )
            elif details.get("spectator_token_hash"):
                app.extensions["room_repository"].remove_spectator(
                    details["room_code"], details["spectator_token_hash"]
                )
        if hasattr(redis_client, "delete"):
            redis_client.delete(socket_key)

    def _reject_spectator():
        redis_client = app.extensions["redis_client"]
        metadata = redis_client.get(f"presence:socket:{request.sid}")
        if metadata and json.loads(metadata).get("role") == "spectator":
            raise ApiError("spectators have read-only access", 403)
