from ..app.errors import ApiError


def socket_credentials(data):
    if not isinstance(data, dict):
        raise ApiError("invalid event payload", 400)
    game_id = data.get("game_id")
    room_code = data.get("room_code")
    token = data.get("player_token")
    if not all(isinstance(item, str) and item for item in (game_id, room_code, token)):
        raise ApiError("game_id, room_code and player_token are required", 400)
    return game_id, room_code.upper(), token
