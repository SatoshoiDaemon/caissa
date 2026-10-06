from datetime import datetime, timezone

from pymongo import ReturnDocument


class MongoRoomRepository:
    def __init__(self, database):
        self.collection = database.rooms
        self.collection.create_index([("access_mode", 1), ("status", 1), ("expires_at", 1)])
        self.collection.create_index("creator_user_id")
        self.collection.create_index("expires_at")
        self.collection.create_index([("status", 1), ("last_activity_at", -1)])

    def create(self, document):
        self.collection.insert_one(document)

    def get(self, room_code):
        room = self.collection.find_one({"_id": room_code})
        if room and room.get("status") != "expired":
            from datetime import datetime, timezone

            expires_at = room.get("expires_at")
            if expires_at and expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at and expires_at <= datetime.now(timezone.utc):
                self.collection.update_one(
                    {"_id": room_code, "status": {"$ne": "active"}},
                    {"$set": {"status": "expired"}},
                )
                room["status"] = "expired"
        return room

    def find_by_game(self, game_id):
        return self.collection.find_one({"game_id": game_id})

    def update_metadata(self, room_code, metadata):
        return (
            self.collection.update_one(
                {"_id": room_code},
                {"$set": {**metadata, "updated_at": datetime.now(timezone.utc)}},
            ).modified_count
            == 1
        )

    def list_public(self, limit, skip, mode=None):
        from datetime import datetime, timezone

        query = {
            "access_mode": "public",
            "status": {"$in": ["waiting", "active", "finished"]},
            "expires_at": {"$gt": datetime.now(timezone.utc)},
        }
        if mode:
            query["mode"] = mode
        return list(
            self.collection.find(query).sort("last_activity_at", -1).skip(skip).limit(limit)
        )

    def assign_black_player(self, room_code, player):
        return (
            self.collection.find_one_and_update(
                {"_id": room_code, "black": None},
                {"$set": {"black": player, "updated_at": datetime.now(timezone.utc)}},
                return_document=ReturnDocument.AFTER,
            )
            is not None
        )

    def add_spectator(self, room_code, spectator, limit):
        result = self.collection.update_one(
            {
                "_id": room_code,
                "status": {"$in": ["waiting", "active"]},
                "$expr": {"$lt": [{"$size": {"$ifNull": ["$spectators", []]}}, limit]},
            },
            {
                "$push": {"spectators": spectator},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
        )
        return result.modified_count == 1

    def remove_spectator(self, room_code, token_hash):
        result = self.collection.update_one(
            {"_id": room_code},
            {"$pull": {"spectators": {"token_hash": token_hash}}},
        )
        return result.modified_count == 1

    def touch(self, room_code, timestamp, status=None):
        update = {"last_activity_at": timestamp, "updated_at": timestamp}
        if status:
            update["status"] = status
        return self.collection.update_one({"_id": room_code}, {"$set": update}).modified_count == 1

    def mark_finished(self, room_code, expires_at):
        return (
            self.collection.update_one(
                {"_id": room_code},
                {
                    "$set": {
                        "status": "finished",
                        "expires_at": expires_at,
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            ).modified_count
            == 1
        )

    def release_black_player(self, room_code):
        return (
            self.collection.update_one(
                {"_id": room_code, "black": {"$ne": None}},
                {"$set": {"black": None, "status": "waiting"}},
            ).modified_count
            == 1
        )

    def mark_active(self, room_code):
        return (
            self.collection.update_one(
                {"_id": room_code},
                {"$set": {"status": "active", "updated_at": datetime.now(timezone.utc)}},
            ).modified_count
            == 1
        )
