import re
import uuid

from ..app.errors import ApiError

POSITION_PATTERN = re.compile(r"^[a-h][1-8]$")
ROOM_PATTERN = re.compile(r"^[A-Z0-9]{8}$")
ROOM_NAME_PATTERN = re.compile(r"^[^\x00-\x1f\x7f]{3,48}$")


def json_body(request):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("invalid JSON body", 400)
    return data


def player_name(value, field="player_name"):
    if not isinstance(value, str):
        raise ApiError(f"{field} must be a string", 400)
    value = value.strip()
    if not 1 <= len(value) <= 32:
        raise ApiError(f"{field} must contain 1 to 32 characters", 400)
    return value


def game_id(value):
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        raise ApiError("invalid game_id", 400)


def room_code(value):
    if not isinstance(value, str) or not ROOM_PATTERN.fullmatch(value.upper()):
        raise ApiError("invalid room_code", 400)
    return value.upper()


def room_name(value):
    if not isinstance(value, str):
        raise ApiError("name must be a string", 400)
    value = value.strip()
    if not ROOM_NAME_PATTERN.fullmatch(value):
        raise ApiError("name must contain 3 to 48 printable characters", 400)
    return value


def pagination(value, default=20):
    try:
        value = int(value) if value is not None else default
    except (TypeError, ValueError):
        raise ApiError("invalid pagination value", 400)
    if not 1 <= value <= 50:
        raise ApiError("pagination value must be between 1 and 50", 400)
    return value


def position(value):
    if not isinstance(value, str) or not POSITION_PATTERN.fullmatch(value):
        raise ApiError("invalid board position", 400)
    return value


def move_payload(data):
    if set(data) - {"from", "to", "promotion"} or "from" not in data or "to" not in data:
        raise ApiError("move must contain only from, to and optional promotion", 400)
    promotion = data.get("promotion")
    if promotion is not None and promotion not in {"q", "r", "b", "n"}:
        raise ApiError("invalid promotion piece", 400)
    return position(data["from"]), position(data["to"]), promotion


def event_id(value):
    if value is None:
        return None
    if not isinstance(value, str) or not 1 <= len(value) <= 64:
        raise ApiError("invalid event_id", 400)
    return value
