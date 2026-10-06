from datetime import datetime, timedelta, timezone

from pymongo import ReturnDocument


class MongoGameRepository:
    def __init__(self, database):
        self.collection = database.games
        self.events = database.game_events

    def create(self, document):
        self.collection.insert_one(document)

    def get(self, game_id):
        return self.collection.find_one({"_id": game_id})

    def list_active(self, limit=200):
        return list(self.collection.find({"status": "active"}).limit(limit))

    def assign_black_player(self, game_id, player):
        return (
            self.collection.update_one(
                {"_id": game_id, "black": None}, {"$set": {"black": player}}
            ).modified_count
            == 1
        )

    def start_clock(self, game_id, timestamp):
        return (
            self.collection.update_one(
                {"_id": game_id, "clock_started_at": None},
                {
                    "$set": {
                        "active_clock_color": "white",
                        "clock_started_at": timestamp,
                        "clock.active_clock_color": "white",
                        "clock.clock_started_at": timestamp,
                    },
                    "$inc": {"clock_version": 1, "clock.clock_version": 1},
                },
            ).modified_count
            == 1
        )

    def release_black_player(self, game_id):
        return (
            self.collection.update_one(
                {"_id": game_id, "black": {"$ne": None}}, {"$set": {"black": None}}
            ).modified_count
            == 1
        )

    def set_player_presence(self, game_id, color, connected, timestamp, socket_id=None):
        update = {
            f"{color}.connected": connected,
            f"{color}.last_seen_at": timestamp,
            f"{color}.socket_id": socket_id if connected else None,
            f"{color}.disconnected_at": None if connected else timestamp,
            f"{color}.reconnect_deadline_at": (
                None if connected else timestamp + timedelta(seconds=60)
            ),
            "last_activity_at": timestamp,
            "updated_at": timestamp,
        }
        return self.collection.update_one({"_id": game_id}, {"$set": update}).modified_count == 1

    def clear_player_presence(self, game_id, color, socket_id):
        now = datetime.now(timezone.utc)
        return (
            self.collection.update_one(
                {"_id": game_id, f"{color}.socket_id": socket_id},
                {
                    "$set": {
                        f"{color}.connected": False,
                        f"{color}.last_seen_at": now,
                        f"{color}.socket_id": None,
                        f"{color}.disconnected_at": now,
                        f"{color}.reconnect_deadline_at": now + timedelta(seconds=60),
                        "updated_at": now,
                    }
                },
            ).modified_count
            == 1
        )

    def update_state(self, game_id, expected_version, document):
        document = dict(document)
        document["updated_at"] = datetime.now(timezone.utc)
        updated = self.collection.find_one_and_update(
            {"_id": game_id, "version": expected_version, "status": "active"},
            {"$set": document, "$inc": {"version": 1}},
            return_document=ReturnDocument.AFTER,
        )
        if updated:
            self.events.insert_one(
                {
                    "game_id": game_id,
                    "version": updated["version"],
                    "type": "state_changed",
                    "state": document,
                    "created_at": updated["updated_at"],
                }
            )
        return updated is not None

    def finish(self, game_id, expected_version, document, status, winner):
        now = datetime.now(timezone.utc)
        updated = self.collection.find_one_and_update(
            {"_id": game_id, "version": expected_version, "status": "active"},
            {
                "$set": dict(document, status=status, winner=winner, updated_at=now),
                "$inc": {"version": 1},
            },
            return_document=ReturnDocument.AFTER,
        )
        if updated:
            self.events.insert_one(
                {
                    "game_id": game_id,
                    "version": updated["version"],
                    "type": "game_finished",
                    "state": dict(document, status=status, winner=winner),
                    "created_at": now,
                }
            )
        return updated is not None
