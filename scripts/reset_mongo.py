import os

from pymongo import MongoClient


def main():
    if os.getenv("RESET_CONFIRM") != "CAISSA":
        raise SystemExit("Set RESET_CONFIRM=CAISSA to confirm destructive database reset")
    uri = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
    database_name = os.getenv("MONGO_DATABASE", "caissa")
    database = MongoClient(uri)[database_name]
    collections = [
        "games",
        "rooms",
        "game_events",
        "users",
        "sessions",
        "recovery_codes",
        "user_game_results",
    ]
    for collection in collections:
        database.drop_collection(collection)
    print(f"Reset database {database_name}: {', '.join(collections)}")


if __name__ == "__main__":
    main()
