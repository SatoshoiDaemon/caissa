import copy


class MemoryUserRepository:
    def __init__(self):
        self.users = {}
        self.sessions = {}
        self.recovery_codes = {}
        self.results = {}

    def create_user(self, document):
        self.users[document["_id"]] = copy.deepcopy(document)

    def get_user(self, user_id):
        value = self.users.get(user_id)
        return copy.deepcopy(value) if value else None

    def get_by_username_key(self, username_key):
        return next(
            (
                copy.deepcopy(value)
                for value in self.users.values()
                if value["username_key"] == username_key
            ),
            None,
        )

    def update_user(self, user_id, update):
        if user_id not in self.users:
            return False
        self.users[user_id].update(copy.deepcopy(update))
        return True

    def create_session(self, document):
        self.sessions[document["_id"]] = copy.deepcopy(document)

    def get_session(self, session_hash):
        return next(
            (
                copy.deepcopy(value)
                for value in self.sessions.values()
                if value["session_hash"] == session_hash
            ),
            None,
        )

    def touch_session(self, session_hash, last_used_at):
        for value in self.sessions.values():
            if value["session_hash"] == session_hash and value.get("revoked_at") is None:
                value["last_used_at"] = last_used_at
                return True
        return False

    def revoke_session(self, session_hash, revoked_at):
        for value in self.sessions.values():
            if value["session_hash"] == session_hash and value.get("revoked_at") is None:
                value["revoked_at"] = revoked_at
                return True
        return False

    def revoke_all_sessions(self, user_id, revoked_at):
        count = 0
        for value in self.sessions.values():
            if value["user_id"] == user_id and value.get("revoked_at") is None:
                value["revoked_at"] = revoked_at
                count += 1
        return count

    def replace_recovery_codes(self, user_id, documents):
        self.recovery_codes[user_id] = copy.deepcopy(documents)

    def get_recovery_codes(self, user_id):
        return copy.deepcopy(self.recovery_codes.get(user_id, []))

    def mark_recovery_used(self, user_id, code_id, used_at):
        for value in self.recovery_codes.get(user_id, []):
            if value["_id"] == code_id and value.get("used_at") is None:
                value["used_at"] = used_at
                return True
        return False

    def record_result(self, document):
        key = (document["game_id"], document["user_id"])
        if key in self.results:
            return False
        self.results[key] = copy.deepcopy(document)
        return True

    def list_results(self, user_id):
        return sorted(
            [
                copy.deepcopy(value)
                for value in self.results.values()
                if value["user_id"] == user_id
            ],
            key=lambda value: value["completed_at"],
            reverse=True,
        )
