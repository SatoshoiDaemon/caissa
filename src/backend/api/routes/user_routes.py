from flask import Blueprint, current_app, jsonify, request

from ...services.account_service import AccountService
from ..schemas import json_body


def _service():
    settings = current_app.extensions["settings"]
    return AccountService(
        current_app.extensions["user_repository"],
        current_app.extensions["redis_client"],
        settings.environment == "production",
    )


def create_user_blueprint():
    blueprint = Blueprint("user_routes", __name__)

    @blueprint.get("/<username>")
    def public_profile(username):
        return jsonify({"user": _service().public_profile(username)})

    @blueprint.get("/<username>/stats")
    def public_stats(username):
        user = _service().repository.get_by_username_key(_service().normalize_username(username))
        if not user:
            from ...app.errors import ApiError

            raise ApiError("user not found", 404)
        return jsonify(_service().stats(user["_id"]))

    @blueprint.get("/<username>/games")
    def public_history(username):
        user = _service().repository.get_by_username_key(_service().normalize_username(username))
        if not user:
            from ...app.errors import ApiError

            raise ApiError("user not found", 404)
        return jsonify({"games": _service().history(user["_id"])})

    @blueprint.patch("/me/profile")
    def update_profile():
        user = _service().current_user()
        return jsonify(
            {
                "user": _service().public_user(
                    _service().update_profile(user["_id"], json_body(request))
                )
            }
        )

    @blueprint.get("/me/stats")
    def stats():
        user = _service().current_user()
        return jsonify(_service().stats(user["_id"]))

    @blueprint.get("/me/games")
    def history():
        user = _service().current_user()
        return jsonify({"games": _service().history(user["_id"])})

    return blueprint
