import hashlib
import re
import secrets
import unicodedata
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from flask import request

from ..app.errors import ApiError
from ..infrastructure.rate_limiter import GameLock

USERNAME_PATTERN = re.compile(r"^[a-z0-9_-]{3,24}$")
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
SESSION_COOKIE = "caissa_session"
SESSION_TTL = timedelta(days=30)
PASSWORD_HASHER = PasswordHasher()


class AccountService:
    def __init__(self, repository, redis_client=None, secure_cookie=False):
        self.repository = repository
        self.redis = redis_client
        self.secure_cookie = secure_cookie

    @staticmethod
    def normalize_username(value):
        if not isinstance(value, str):
            raise ApiError("invalid username or password", 400)
        username = value.strip().lower()
        if not USERNAME_PATTERN.fullmatch(username):
            raise ApiError("username must contain 3 to 24 lowercase letters, numbers, _ or -", 400)
        return username

    @staticmethod
    def validate_password(value):
        if not isinstance(value, str) or len(value) < 12 or len(value) > 256:
            raise ApiError("password must contain 12 to 256 characters", 400)
        return value

    @staticmethod
    def validate_profile(update):
        allowed = {"bio", "status_emoji", "status_message", "profile_image_url", "timezone"}
        if set(update) - allowed:
            raise ApiError("invalid profile fields", 400)
        result = {}
        if "bio" in update:
            if not isinstance(update["bio"], str) or len(update["bio"]) > 500:
                raise ApiError("bio must contain at most 500 characters", 400)
            result["bio"] = update["bio"].strip()
        if "status_message" in update:
            if not isinstance(update["status_message"], str) or len(update["status_message"]) > 64:
                raise ApiError("status_message must contain at most 64 characters", 400)
            result["status_message"] = update["status_message"].strip()
        if "status_emoji" in update:
            emoji = update["status_emoji"] or None
            if emoji and (
                len(emoji) > 8
                or any(unicodedata.category(char) not in {"So", "Sk", "Mn", "Cf"} for char in emoji)
            ):
                raise ApiError("status_emoji is invalid", 400)
            result["status_emoji"] = emoji
        if "profile_image_url" in update:
            value = update["profile_image_url"] or None
            if value:
                parsed = urlsplit(value)
                if parsed.scheme != "https" or not parsed.netloc or len(value) > 2048:
                    raise ApiError("profile_image_url must be an HTTPS URL", 400)
            result["profile_image_url"] = value
        if "timezone" in update:
            value = update["timezone"]
            try:
                ZoneInfo(value)
            except (ZoneInfoNotFoundError, TypeError):
                raise ApiError("invalid timezone", 400)
            result["timezone"] = value
        return result

    def register(self, username, password, user_agent=None):
        username = self.normalize_username(username)
        password = self.validate_password(password)
        if self.repository.get_by_username_key(username):
            raise ApiError("username is already in use", 409)
        now = datetime.now(timezone.utc)
        user_id = str(uuid.uuid4())
        user = {
            "_id": user_id,
            "username": username,
            "username_key": username,
            "password_hash": PASSWORD_HASHER.hash(password),
            "bio": "",
            "status_emoji": None,
            "status_message": "",
            "profile_image_url": None,
            "timezone": "UTC",
            "created_at": now,
            "updated_at": now,
        }
        self.repository.create_user(user)
        codes = self._replace_recovery_codes(user_id, now)
        session_token = self._create_session(user_id, user_agent, now)
        return self.public_user(user), codes, session_token

    def login(self, username, password, user_agent=None):
        username = self.normalize_username(username)
        password = self.validate_password(password)
        user = self.repository.get_by_username_key(username)
        if not user or not self._verify_password(user["password_hash"], password):
            raise ApiError("invalid username or password", 401)
        return self.public_user(user), self._create_session(user["_id"], user_agent)

    def current_user(self, flask_request=None):
        request_obj = flask_request or request
        raw_token = request_obj.cookies.get(SESSION_COOKIE)
        if not raw_token:
            raise ApiError("authentication required", 401)
        session = self.repository.get_session(self._hash_token(raw_token))
        now = datetime.now(timezone.utc)
        if not session or session.get("revoked_at") or self._as_aware(session["expires_at"]) <= now:
            raise ApiError("authentication required", 401)
        user = self.repository.get_user(session["user_id"])
        if not user:
            raise ApiError("authentication required", 401)
        self.repository.touch_session(self._hash_token(raw_token), now)
        return user

    def optional_current_user(self, flask_request=None):
        try:
            return self.current_user(flask_request)
        except ApiError as error:
            if error.status_code == 401:
                return None
            raise

    def logout(self, flask_request=None):
        request_obj = flask_request or request
        raw_token = request_obj.cookies.get(SESSION_COOKIE)
        if raw_token:
            self.repository.revoke_session(self._hash_token(raw_token), datetime.now(timezone.utc))

    def update_profile(self, user_id, update):
        clean = self.validate_profile(update)
        if clean:
            self.repository.update_user(user_id, clean)
        return self.get_user(user_id)

    def change_password(self, user_id, new_password, current_password=None, recovery_code=None):
        new_password = self.validate_password(new_password)
        user = self.get_user(user_id)
        authorized = bool(
            current_password and self._verify_password(user["password_hash"], current_password)
        )
        if not authorized and recovery_code:
            with self._account_lock(user_id):
                self._consume_recovery_code(user, recovery_code)
                authorized = True
        if not authorized:
            raise ApiError("current password or recovery code is invalid", 401)
        self.repository.update_user(user_id, {"password_hash": PASSWORD_HASHER.hash(new_password)})
        self.repository.revoke_all_sessions(user_id, datetime.now(timezone.utc))
        return self.get_user(user_id)

    def recover(self, username, recovery_code, new_password):
        username = self.normalize_username(username)
        new_password = self.validate_password(new_password)
        user = self.repository.get_by_username_key(username)
        if not user:
            raise ApiError("recovery failed", 401)
        with self._account_lock(user["_id"]):
            self._consume_recovery_code(user, recovery_code)
            self.repository.update_user(
                user["_id"], {"password_hash": PASSWORD_HASHER.hash(new_password)}
            )
            self.repository.revoke_all_sessions(user["_id"], datetime.now(timezone.utc))
        return self.public_user(self.get_user(user["_id"]))

    def rotate_recovery_codes(self, user_id, current_password=None, recovery_code=None):
        user = self.get_user(user_id)
        if not (
            current_password and self._verify_password(user["password_hash"], current_password)
        ):
            with self._account_lock(user_id):
                self._consume_recovery_code(user, recovery_code or "")
        return self._replace_recovery_codes(user_id, datetime.now(timezone.utc))

    def get_user(self, user_id):
        user = self.repository.get_user(user_id)
        if not user:
            raise ApiError("user not found", 404)
        return user

    def public_user(self, user):
        emoji = user.get("status_emoji") or ""
        message = user.get("status_message") or ""
        return {
            "user_id": user["_id"],
            "username": user["username"],
            "bio": user.get("bio", ""),
            "status_emoji": emoji or None,
            "status_message": message,
            "status": f"{emoji} {message}".strip(),
            "profile_image_url": user.get("profile_image_url"),
            "timezone": user.get("timezone", "UTC"),
            "created_at": self._serialize_datetime(user.get("created_at")),
        }

    def public_profile(self, username):
        user = self.repository.get_by_username_key(self.normalize_username(username))
        if not user:
            raise ApiError("user not found", 404)
        return self.public_user(user)

    def stats(self, user_id):
        user = self.get_user(user_id)
        results = self.repository.list_results(user_id)
        zone = ZoneInfo(user.get("timezone", "UTC"))
        now = datetime.now(timezone.utc).astimezone(zone)
        week_start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return {
            "overall": self._aggregate(results),
            "week": self._aggregate(
                [
                    result
                    for result in results
                    if self._result_date(result).astimezone(zone) >= week_start
                ]
            ),
            "month": self._aggregate(
                [
                    result
                    for result in results
                    if self._result_date(result).astimezone(zone) >= month_start
                ]
            ),
        }

    def history(self, user_id):
        return [self._public_result(result) for result in self.repository.list_results(user_id)]

    def record_result(self, document):
        return self.repository.record_result(document)

    def _replace_recovery_codes(self, user_id, now):
        plain_codes = [self._new_recovery_code() for _ in range(6)]
        documents = [
            {
                "_id": str(uuid.uuid4()),
                "user_id": user_id,
                "code_hash": PASSWORD_HASHER.hash(code.replace("-", "")),
                "created_at": now,
                "used_at": None,
            }
            for code in plain_codes
        ]
        self.repository.replace_recovery_codes(user_id, documents)
        return plain_codes

    def _consume_recovery_code(self, user, provided_code):
        if not isinstance(provided_code, str):
            raise ApiError("recovery failed", 401)
        normalized = provided_code.replace("-", "").upper()
        for code in self.repository.get_recovery_codes(user["_id"]):
            try:
                valid = PASSWORD_HASHER.verify(code["code_hash"], normalized)
            except (VerificationError, VerifyMismatchError, InvalidHashError):
                valid = False
            if valid and self.repository.mark_recovery_used(
                user["_id"], code["_id"], datetime.now(timezone.utc)
            ):
                return True
        raise ApiError("recovery failed", 401)

    def _create_session(self, user_id, user_agent=None, now=None):
        now = now or datetime.now(timezone.utc)
        raw = secrets.token_urlsafe(32)
        self.repository.create_session(
            {
                "_id": str(uuid.uuid4()),
                "user_id": user_id,
                "session_hash": self._hash_token(raw),
                "created_at": now,
                "expires_at": now + SESSION_TTL,
                "last_used_at": now,
                "revoked_at": None,
                "user_agent": (user_agent or "")[:256],
            }
        )
        return raw

    @staticmethod
    def _hash_token(token):
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def _verify_password(password_hash, password):
        try:
            return PASSWORD_HASHER.verify(password_hash, password)
        except (VerificationError, VerifyMismatchError, InvalidHashError):
            return False

    @staticmethod
    def _new_recovery_code():
        raw = "".join(secrets.choice(CODE_ALPHABET) for _ in range(16))
        return "-".join(raw[index : index + 4] for index in range(0, 16, 4))

    def _account_lock(self, user_id):
        return GameLock(self.redis, f"account:{user_id}") if self.redis else _NullLock()

    @staticmethod
    def _aggregate(results):
        wins = sum(result["result"] == "win" for result in results)
        losses = sum(result["result"] == "loss" for result in results)
        draws = sum(result["result"] == "draw" for result in results)
        total = wins + losses + draws
        return {
            "wins": wins,
            "losses": losses,
            "draws": draws,
            "total": total,
            "win_rate": round(wins / total * 100, 2) if total else 0,
        }

    @staticmethod
    def _result_date(result):
        return AccountService._as_aware(result["completed_at"])

    @staticmethod
    def _public_result(result):
        return {
            key: result.get(key)
            for key in (
                "game_id",
                "opponent_user_id",
                "color",
                "result",
                "status",
                "mode",
                "completed_at",
            )
        }

    @staticmethod
    def _as_aware(value):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value

    @staticmethod
    def _serialize_datetime(value):
        return value.isoformat() if isinstance(value, datetime) else value


class _NullLock:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False
