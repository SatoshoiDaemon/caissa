import hashlib
import secrets
from datetime import datetime, timezone

from ..app.errors import ApiError


class RoomService:
    def __init__(self, room_repository, game_repository, spectator_limit=50):
        self.rooms = room_repository
        self.games = game_repository
        self.spectator_limit = spectator_limit

    def get(self, room_code):
        room = self.rooms.get(room_code)
        if not room or room.get("status") == "expired":
            raise ApiError("room not found", 404)
        return self.serialize(room)

    def list_public(self, limit=20, offset=0, mode=None):
        limit = min(max(limit, 1), 50)
        offset = max(offset, 0)
        rooms = self.rooms.list_public(limit, offset, mode)
        return {
            "rooms": [self.serialize(room, include_code=False) for room in rooms],
            "limit": limit,
            "offset": offset,
        }

    def issue_spectator(self, room_code):
        room = self.rooms.get(room_code)
        if not room or room.get("status") == "expired":
            raise ApiError("room not found", 404)
        if room.get("access_mode", "public") != "public":
            raise ApiError("room is not public", 403)
        raw_token = secrets.token_urlsafe(32)
        spectator = {
            "spectator_id": secrets.token_hex(16),
            "token_hash": self.hash_token(raw_token),
            "created_at": datetime.now(timezone.utc),
            "expires_at": room.get("expires_at"),
        }
        if not self.rooms.add_spectator(room_code, spectator, self.spectator_limit):
            raise ApiError("spectator limit reached", 409)
        return raw_token, self.serialize(self.rooms.get(room_code))

    def authenticate_spectator(self, room_code, token):
        room = self.rooms.get(room_code)
        if not room or room.get("status") == "expired":
            raise ApiError("room not found", 404)
        token_hash = self.hash_token(token)
        for spectator in room.get("spectators", []):
            if secrets.compare_digest(spectator.get("token_hash", ""), token_hash):
                expires_at = spectator.get("expires_at")
                if expires_at and expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if expires_at and expires_at <= datetime.now(timezone.utc):
                    raise ApiError("spectator token expired", 401)
                return spectator
        raise ApiError("invalid spectator token", 401)

    @staticmethod
    def hash_token(token):
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def serialize(room, include_code=True):
        black = room.get("black") or {}
        white = room.get("white") or {}
        spectators = room.get("spectators") or []
        result = {
            "room_code": room.get("_id"),
            "game_id": room.get("game_id"),
            "name": room.get("name") or f"{white.get('name', 'Caissa')} room",
            "creator": room.get("creator_snapshot") or white.get("profile_snapshot"),
            "white_player": white.get("name"),
            "black_player": black.get("name"),
            "white_profile": white.get("profile_snapshot"),
            "black_profile": black.get("profile_snapshot"),
            "spectator_count": len(spectators),
            "status": room.get("status", "waiting"),
            "access_mode": room.get("access_mode", "code_only"),
            "mode": room.get("mode", "online"),
            "clock": RoomService._json_clock(room.get("clock") or {}, room.get("status")),
            "created_at": RoomService._json_date(room.get("created_at")),
            "last_activity_at": RoomService._json_date(room.get("last_activity_at")),
            "expires_at": RoomService._json_date(room.get("expires_at")),
        }
        if not include_code and result["access_mode"] == "code_only":
            result.pop("room_code", None)
        return result

    @staticmethod
    def _json_date(value):
        return value.isoformat() if isinstance(value, datetime) else value

    @staticmethod
    def _json_clock(clock, status=None):
        value = dict(clock)
        started_at = value.get("clock_started_at", value.get("started_at"))
        active_color = value.get("active_clock_color", value.get("active_color"))
        if status == "active" and active_color and isinstance(started_at, datetime):
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
            elapsed = max(0, int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000))
            key = f"{active_color}_time_remaining_ms"
            if key not in value:
                key = f"{active_color}_time_ms"
            if isinstance(value.get(key), int):
                value[key] = max(0, value[key] - elapsed)
        value["clock_started_at"] = RoomService._json_date(started_at)
        value.pop("started_at", None)
        return value
