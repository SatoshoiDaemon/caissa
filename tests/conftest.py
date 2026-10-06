import copy
from datetime import datetime, timedelta, timezone

import pytest

from backend.app import create_app
from backend.app.config import Settings


class FakeLock:
    def __init__(self, _key, **_kwargs):
        self.acquired = False

    def acquire(self, **_kwargs):
        self.acquired = True
        return True

    def release(self):
        self.acquired = False


class FakeRedis:
    def __init__(self):
        self.values = {}

    def incr(self, key):
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    def expire(self, _key, _seconds):
        return True

    def get(self, key):
        return self.values.get(key)

    def setex(self, key, _seconds, value):
        self.values[key] = value
        return True

    def delete(self, key):
        self.values.pop(key, None)
        return True

    def publish(self, _channel, _message):
        return 1

    def lock(self, key, **kwargs):
        return FakeLock(key, **kwargs)


class FakeGameRepository:
    def __init__(self):
        self.documents = {}

    def create(self, document):
        self.documents[document["_id"]] = copy.deepcopy(document)

    def get(self, game_id):
        value = self.documents.get(game_id)
        return copy.deepcopy(value) if value else None

    def assign_black_player(self, game_id, player):
        document = self.documents.get(game_id)
        if not document or document.get("black") is not None:
            return False
        document["black"] = copy.deepcopy(player)
        return True

    def start_clock(self, game_id, timestamp):
        document = self.documents[game_id]
        if document.get("clock", {}).get("started_at") is not None:
            return False
        document["clock"].update({"active_clock_color": "white", "clock_started_at": timestamp})
        document.update({"active_clock_color": "white", "clock_started_at": timestamp})
        return True

    def release_black_player(self, game_id):
        document = self.documents.get(game_id)
        if not document or document.get("black") is None:
            return False
        document["black"] = None
        return True

    def set_player_presence(self, game_id, color, connected, timestamp, socket_id=None):
        document = self.documents[game_id]
        document[color].update(
            {
                "connected": connected,
                "last_seen_at": timestamp,
                "socket_id": socket_id,
                "disconnected_at": None if connected else timestamp,
                "reconnect_deadline_at": None if connected else timestamp + timedelta(seconds=60),
            }
        )
        document["last_activity_at"] = timestamp
        return True

    def clear_player_presence(self, game_id, color, socket_id):
        document = self.documents[game_id]
        if document[color].get("socket_id") != socket_id:
            return False
        document[color].update(
            {
                "connected": False,
                "last_seen_at": datetime.now(timezone.utc),
                "socket_id": None,
                "disconnected_at": datetime.now(timezone.utc),
                "reconnect_deadline_at": datetime.now(timezone.utc) + timedelta(seconds=60),
            }
        )
        return True

    def update_state(self, game_id, expected_version, document):
        current = self.documents.get(game_id)
        if not current or current["version"] != expected_version or current["status"] != "active":
            return False
        current.update(copy.deepcopy(document))
        current["version"] += 1
        current["updated_at"] = datetime.now(timezone.utc)
        return True

    def finish(self, game_id, expected_version, document, status, winner):
        current = self.documents.get(game_id)
        if not current or current["version"] != expected_version or current["status"] != "active":
            return False
        current.update(copy.deepcopy(document))
        current.update({"status": status, "winner": winner, "version": expected_version + 1})
        return True


class FakeRoomRepository:
    def __init__(self):
        self.documents = {}

    def create(self, document):
        self.documents[document["_id"]] = copy.deepcopy(document)

    def get(self, room_code):
        value = self.documents.get(room_code)
        return copy.deepcopy(value) if value else None

    def list_public(self, limit, skip, mode=None):
        values = [
            value
            for value in self.documents.values()
            if value.get("access_mode") == "public"
            and value.get("status") in {"waiting", "active", "finished"}
            and (mode is None or value.get("mode") == mode)
        ]
        return copy.deepcopy(values[skip : skip + limit])

    def update_metadata(self, room_code, metadata):
        if room_code not in self.documents:
            return False
        self.documents[room_code].update(copy.deepcopy(metadata))
        return True

    def find_by_game(self, game_id):
        return next(
            (
                copy.deepcopy(value)
                for value in self.documents.values()
                if value["game_id"] == game_id
            ),
            None,
        )

    def add_spectator(self, room_code, spectator, limit):
        document = self.documents.get(room_code)
        if not document or len(document.get("spectators", [])) >= limit:
            return False
        document.setdefault("spectators", []).append(copy.deepcopy(spectator))
        return True

    def remove_spectator(self, room_code, token_hash):
        document = self.documents.get(room_code)
        if not document:
            return False
        before = len(document.get("spectators", []))
        document["spectators"] = [
            value
            for value in document.get("spectators", [])
            if value.get("token_hash") != token_hash
        ]
        return len(document["spectators"]) != before

    def touch(self, room_code, timestamp, status=None):
        document = self.documents.get(room_code)
        if not document:
            return False
        document["last_activity_at"] = timestamp
        if status:
            document["status"] = status
        return True

    def mark_finished(self, room_code, expires_at):
        document = self.documents.get(room_code)
        if not document:
            return False
        document.update({"status": "finished", "expires_at": expires_at})
        return True

    def assign_black_player(self, room_code, player):
        document = self.documents.get(room_code)
        if not document or document.get("black") is not None:
            return False
        document["black"] = copy.deepcopy(player)
        return True

    def release_black_player(self, room_code):
        document = self.documents.get(room_code)
        if not document or document.get("black") is None:
            return False
        document["black"] = None
        document["status"] = "waiting"
        return True

    def mark_active(self, room_code):
        document = self.documents.get(room_code)
        if not document:
            return False
        document["status"] = "active"
        return True


@pytest.fixture
def repositories():
    return FakeGameRepository(), FakeRoomRepository()


@pytest.fixture
def app(repositories):
    game_repository, room_repository = repositories
    settings = Settings(
        secret_key="test-secret",
        mongo_uri="mongodb://unused",
        mongo_database="unused",
        redis_url="redis://unused",
        host="127.0.0.1",
        port=5000,
        debug=False,
        environment="testing",
        allowed_origins=["http://localhost:5000"],
        testing=True,
    )
    return create_app(settings, game_repository, room_repository, FakeRedis())


@pytest.fixture
def client(app):
    return app.test_client()
