from datetime import datetime, timezone

from pymongo import ASCENDING, DESCENDING, ReturnDocument


class MongoUserRepository:
    def __init__(self, database):
        self.users = database.users
        self.sessions = database.sessions
        self.recovery_codes = database.recovery_codes
        self.results = database.user_game_results

    def create_user(self, document):
        self.users.insert_one(document)

    def get_user(self, user_id):
        return self.users.find_one({"_id": user_id})

    def get_by_username_key(self, username_key):
        return self.users.find_one({"username_key": username_key})

    def update_user(self, user_id, update):
        update = dict(update)
        update["updated_at"] = datetime.now(timezone.utc)
        return self.users.update_one({"_id": user_id}, {"$set": update}).modified_count == 1

    def create_session(self, document):
        self.sessions.insert_one(document)

    def get_session(self, session_hash):
        return self.sessions.find_one({"session_hash": session_hash})

    def touch_session(self, session_hash, last_used_at):
        return (
            self.sessions.update_one(
                {"session_hash": session_hash, "revoked_at": None},
                {"$set": {"last_used_at": last_used_at}},
            ).modified_count
            == 1
        )

    def revoke_session(self, session_hash, revoked_at):
        return (
            self.sessions.update_one(
                {"session_hash": session_hash, "revoked_at": None},
                {"$set": {"revoked_at": revoked_at}},
            ).modified_count
            == 1
        )

    def revoke_all_sessions(self, user_id, revoked_at):
        return self.sessions.update_many(
            {"user_id": user_id, "revoked_at": None},
            {"$set": {"revoked_at": revoked_at}},
        ).modified_count

    def replace_recovery_codes(self, user_id, documents):
        self.recovery_codes.delete_many({"user_id": user_id, "used_at": None})
        if documents:
            self.recovery_codes.insert_many(documents)

    def get_recovery_codes(self, user_id):
        return list(self.recovery_codes.find({"user_id": user_id, "used_at": None}))

    def mark_recovery_used(self, user_id, code_id, used_at):
        return (
            self.recovery_codes.find_one_and_update(
                {"_id": code_id, "user_id": user_id, "used_at": None},
                {"$set": {"used_at": used_at}},
                return_document=ReturnDocument.AFTER,
            )
            is not None
        )

    def record_result(self, document):
        result = self.results.update_one(
            {"game_id": document["game_id"], "user_id": document["user_id"]},
            {"$setOnInsert": document},
            upsert=True,
        )
        return result.upserted_id is not None

    def list_results(self, user_id):
        return list(self.results.find({"user_id": user_id}).sort("completed_at", DESCENDING))


def ensure_user_indexes(database):
    database.users.create_index("username_key", unique=True)
    database.sessions.create_index("session_hash", unique=True)
    database.sessions.create_index("expires_at", expireAfterSeconds=0)
    database.recovery_codes.create_index([("user_id", ASCENDING), ("used_at", ASCENDING)])
    database.user_game_results.create_index(
        [("game_id", ASCENDING), ("user_id", ASCENDING)], unique=True
    )
    database.user_game_results.create_index([("user_id", ASCENDING), ("completed_at", DESCENDING)])
