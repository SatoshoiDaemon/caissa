from flask import Blueprint, current_app, jsonify, request

from ...app.errors import ApiError
from ...infrastructure.rate_limiter import RedisRateLimiter
from ...services.account_service import SESSION_COOKIE, SESSION_TTL, AccountService
from ..schemas import json_body


def _service():
    settings = current_app.extensions["settings"]
    return AccountService(
        current_app.extensions["user_repository"],
        current_app.extensions["redis_client"],
        settings.environment == "production",
    )


def _limit(key, limit=10):
    if not RedisRateLimiter(current_app.extensions["redis_client"]).allow(key, limit, 60):
        raise ApiError("rate limit exceeded", 429)


def _set_session_cookie(response, token):
    settings = current_app.extensions["settings"]
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,
        secure=settings.environment == "production",
        samesite="Lax",
        path="/",
    )
    return response


def _clear_session_cookie(response):
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


def create_auth_blueprint():
    blueprint = Blueprint("auth_routes", __name__)

    @blueprint.post("/register")
    def register():
        _limit(f"register:{request.remote_addr}")
        data = json_body(request)
        user, recovery_codes, token = _service().register(
            data.get("username"), data.get("password"), request.headers.get("User-Agent")
        )
        response = jsonify(
            {
                "user": user,
                "recovery_codes": recovery_codes,
                "recovery_warning": "These codes are shown once. Store them securely; losing them and your password permanently loses the account.",
            }
        )
        response.status_code = 201
        return _set_session_cookie(response, token)

    @blueprint.post("/login")
    def login():
        data = json_body(request)
        username_key = str(data.get("username", "")).strip().lower()[:64]
        _limit(f"login:{request.remote_addr}:{username_key}", 10)
        user, token = _service().login(
            data.get("username"), data.get("password"), request.headers.get("User-Agent")
        )
        return _set_session_cookie(jsonify({"user": user}), token)

    @blueprint.post("/logout")
    def logout():
        _service().logout(request)
        return _clear_session_cookie(jsonify({"ok": True}))

    @blueprint.get("/me")
    def me():
        return jsonify({"user": _service().public_user(_service().current_user())})

    @blueprint.post("/password")
    def change_password():
        _limit(f"password:{request.remote_addr}")
        user = _service().current_user()
        data = json_body(request)
        updated = _service().change_password(
            user["_id"],
            data.get("new_password"),
            current_password=data.get("current_password"),
            recovery_code=data.get("recovery_code"),
        )
        return _clear_session_cookie(
            jsonify({"user": _service().public_user(updated), "sessions_revoked": True})
        )

    @blueprint.post("/recovery")
    def recovery():
        _limit(f"recovery:{request.remote_addr}")
        data = json_body(request)
        user = _service().recover(
            data.get("username"), data.get("recovery_code"), data.get("new_password")
        )
        return jsonify({"user": user, "sessions_revoked": True})

    @blueprint.post("/recovery-codes")
    def recovery_codes():
        _limit(f"recovery-codes:{request.remote_addr}")
        user = _service().current_user()
        data = json_body(request)
        codes = _service().rotate_recovery_codes(
            user["_id"], data.get("current_password"), data.get("recovery_code")
        )
        return jsonify(
            {
                "recovery_codes": codes,
                "recovery_warning": "These codes are shown once. Store them securely.",
            }
        )

    return blueprint
