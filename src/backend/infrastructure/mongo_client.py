from pymongo import ASCENDING, MongoClient

from .repositories.mongo_user_repository import ensure_user_indexes


def get_mongo_database(settings):
    client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=3000)
    database = client[settings.mongo_database]
    database.games.create_index([("status", ASCENDING), ("updated_at", ASCENDING)])
    database.rooms.create_index("game_id", unique=True)
    database.game_events.create_index([("game_id", ASCENDING), ("version", ASCENDING)], unique=True)
    ensure_user_indexes(database)
    return database
