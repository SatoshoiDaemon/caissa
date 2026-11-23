"""Run Flask and Socket.IO with isolated repository storage for browser tests."""

from dataclasses import replace

import fakeredis
import mongomock

from backend.app import create_app
from backend.app.config import Settings
from backend.app.extensions import socketio
from backend.infrastructure.repositories.mongo_game_repository import MongoGameRepository
from backend.infrastructure.repositories.mongo_room_repository import MongoRoomRepository
from backend.infrastructure.repositories.mongo_user_repository import MongoUserRepository

settings = replace(Settings.from_environment(), environment="testing", testing=True)
database = mongomock.MongoClient(tz_aware=True).caissa_browser_tests
app = create_app(
    settings,
    MongoGameRepository(database),
    MongoRoomRepository(database),
    fakeredis.FakeRedis(),
    MongoUserRepository(database),
)
socketio.run(app, host=settings.host, port=settings.port, allow_unsafe_werkzeug=True)
