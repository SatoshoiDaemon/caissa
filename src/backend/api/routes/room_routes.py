from flask import Blueprint, current_app, jsonify, request

from ...app.errors import ApiError
from ...infrastructure.rate_limiter import RedisRateLimiter
from ...services.account_service import AccountService
from ...services.game_service import CLOCK_PRESETS, GameService
from ...services.room_service import RoomService
from ..schemas import json_body, pagination, player_name, room_name
from ..schemas import room_code as validate_room_code


def create_room_blueprint():
    blueprint = Blueprint("room_routes", __name__)

    def games():
        return current_app.extensions["game_repository"]

    def rooms():
        return current_app.extensions["room_repository"]

    def account():
        return AccountService(
            current_app.extensions["user_repository"], current_app.extensions["redis_client"]
        )

    @blueprint.get("")
    def list_rooms():
        limit = pagination(request.args.get("limit"))
        try:
            offset = max(0, int(request.args.get("offset", 0)))
        except ValueError:
            raise ApiError("invalid offset", 400)
        mode = request.args.get("mode")
        if mode and mode not in {"bullet", "blitz", "rapid", "classical"}:
            raise ApiError("invalid game mode", 400)
        return jsonify(RoomService(rooms(), games()).list_public(limit, offset, mode))

    @blueprint.post("")
    def create_public_room():
        if not RedisRateLimiter(current_app.extensions["redis_client"]).allow(
            f"room-create:{request.remote_addr}", 10, 60
        ):
            raise ApiError("rate limit exceeded", 429)
        user = account().optional_current_user()
        if not user:
            raise ApiError("authentication required", 401)
        data = json_body(request)
        name = room_name(data.get("name"))
        access_mode = data.get("access_mode", "public")
        mode = data.get("mode", "blitz")
        if mode not in CLOCK_PRESETS:
            raise ApiError("invalid game mode", 400)
        preset = CLOCK_PRESETS[mode]
        # Client clock values are deliberately ignored; the selected mode is authoritative.
        initial_time = preset["time_ms"] // 1000
        increment = preset["increment_ms"] // 1000
        state, token, code = GameService(
            games(),
            rooms(),
            current_app.extensions["redis_client"],
            current_app.extensions["user_repository"],
        ).create_room(
            user,
            name,
            access_mode,
            mode,
            initial_time,
            increment,
        )
        return (
            jsonify(
                {
                    "room_code": code,
                    "game_id": state["game_id"],
                    "player_color": "white",
                    "player_token": token,
                    "room": RoomService(rooms(), games()).get(code),
                    "game_state": state,
                }
            ),
            201,
        )

    @blueprint.get("/<room_code>")
    def get_room(room_code):
        code = validate_room_code(room_code)
        room = RoomService(rooms(), games()).get(code)
        try:
            room["game_state"] = GameService(
                games(), rooms(), current_app.extensions["redis_client"]
            ).get_state(room["game_id"])
        except ApiError:
            pass
        return jsonify(room)

    @blueprint.post("/<room_code>/spectate")
    def spectate_room(room_code):
        code = validate_room_code(room_code)
        if not RedisRateLimiter(current_app.extensions["redis_client"]).allow(
            f"spectate:{request.remote_addr}:{code}", 20, 60
        ):
            raise ApiError("rate limit exceeded", 429)
        token, room = RoomService(rooms(), games()).issue_spectator(code)
        room["game_state"] = GameService(
            games(), rooms(), current_app.extensions["redis_client"]
        ).get_state(room["game_id"])
        return jsonify({"room_code": code, "spectator_token": token, "room": room}), 200

    @blueprint.post("/<room_code>/join")
    def join_room(room_code):
        if not RedisRateLimiter(current_app.extensions["redis_client"]).allow(
            f"join:{request.remote_addr}", 20, 60
        ):
            raise ApiError("rate limit exceeded", 429)
        code = validate_room_code(room_code)
        data = json_body(request)
        name = player_name(data.get("player_name")) if data.get("player_name") else None
        auth_header = request.headers.get("Authorization", "")
        token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else None
        account = AccountService(
            current_app.extensions["user_repository"], current_app.extensions["redis_client"]
        )
        user = account.optional_current_user()
        result, token, _, color = GameService(
            games(),
            rooms(),
            current_app.extensions["redis_client"],
            current_app.extensions["user_repository"],
        ).join_room(code, name, token, user)
        return (
            jsonify(
                {
                    "game_id": result["game_id"],
                    "room_code": code,
                    "player_color": color,
                    "player_token": token,
                    "game_state": result,
                }
            ),
            200,
        )

    @blueprint.post("/<room_code>/draw")
    def offer_draw(room_code):
        return jsonify({"status": "draw_offered", "room_code": validate_room_code(room_code)})

    return blueprint
