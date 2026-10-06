import hashlib
import hmac
import secrets

from ..app.errors import ApiError


class PlayerService:
    @staticmethod
    def issue_token():
        token = secrets.token_urlsafe(32)
        return token, hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def verify_token(token, expected_hash):
        if not token or not expected_hash:
            raise ApiError("authentication required", 401)
        actual_hash = hashlib.sha256(token.encode()).hexdigest()
        if not hmac.compare_digest(actual_hash, expected_hash):
            raise ApiError("invalid player token", 401)
        return True

    @staticmethod
    def bearer_token(request):
        value = request.headers.get("Authorization", "")
        if not value.startswith("Bearer "):
            raise ApiError("authentication required", 401)
        return value[7:].strip()
