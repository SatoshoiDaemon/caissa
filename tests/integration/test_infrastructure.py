import os
import uuid

import pytest


@pytest.mark.integration
def test_mongo_and_redis_are_reachable():
    if os.getenv("RUN_INTEGRATION_TESTS") != "true":
        pytest.skip("set RUN_INTEGRATION_TESTS=true to run service integration tests")

    from pymongo import MongoClient
    from redis import Redis

    mongo = MongoClient(
        os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017"), serverSelectionTimeoutMS=2000
    )
    redis_client = Redis.from_url(os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"))
    assert mongo.admin.command("ping")["ok"] == 1
    assert redis_client.ping() is True


@pytest.mark.integration
def test_game_state_survives_application_restart():
    if os.getenv("RUN_INTEGRATION_TESTS") != "true":
        pytest.skip("set RUN_INTEGRATION_TESTS=true to run service integration tests")

    from pymongo import MongoClient

    from backend.app import create_app
    from backend.app.config import Settings

    mongo_uri = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
    redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    database_name = f"caissa_phase_31_{uuid.uuid4().hex}"
    settings = Settings(
        secret_key="integration-secret",
        mongo_uri=mongo_uri,
        mongo_database=database_name,
        redis_url=redis_url,
        host="127.0.0.1",
        port=5000,
        debug=False,
        environment="testing",
        allowed_origins=["http://localhost:5000"],
        testing=True,
    )
    mongo = MongoClient(mongo_uri)
    try:
        first_app = create_app(settings)
        first_client = first_app.test_client()
        game = first_client.post("/api/v1/games", json={"player_name": "Alice"}).get_json()
        first_client.post(
            f"/api/v1/games/{game['game_id']}/moves",
            headers={"Authorization": f"Bearer {game['player_token']}"},
            json={"from": "e2", "to": "e4"},
        )

        restarted_app = create_app(settings)
        restored = restarted_app.test_client().get(f"/api/v1/games/{game['game_id']}").get_json()

        assert restored["fen"].endswith(" b KQkq e3 0 1")
        assert restored["version"] == 1
        assert restored["move_history"][0]["from"] == "e2"
    finally:
        mongo.drop_database(database_name)


@pytest.mark.integration
def test_account_and_session_survive_application_restart():
    if os.getenv("RUN_INTEGRATION_TESTS") != "true":
        pytest.skip("set RUN_INTEGRATION_TESTS=true to run service integration tests")

    from pymongo import MongoClient

    from backend.app import create_app
    from backend.app.config import Settings

    mongo_uri = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
    redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    database_name = f"caissa_accounts_{uuid.uuid4().hex}"
    settings = Settings(
        secret_key="integration-secret",
        mongo_uri=mongo_uri,
        mongo_database=database_name,
        redis_url=redis_url,
        host="127.0.0.1",
        port=5000,
        debug=False,
        environment="testing",
        allowed_origins=["http://localhost:5000"],
        testing=True,
    )
    mongo = MongoClient(mongo_uri)
    try:
        first_client = create_app(settings).test_client()
        registration = first_client.post(
            "/api/v1/auth/register",
            json={"username": "persistent_user", "password": "correct horse battery"},
        )
        assert registration.status_code == 201
        cookie = first_client.get_cookie("caissa_session")

        restarted_client = create_app(settings).test_client()
        restarted_client.set_cookie("caissa_session", cookie.value)
        current = restarted_client.get("/api/v1/auth/me")

        assert current.status_code == 200
        assert current.get_json()["user"]["username"] == "persistent_user"
    finally:
        mongo.drop_database(database_name)


@pytest.mark.integration
def test_public_room_and_spectator_survive_application_restart():
    if os.getenv("RUN_INTEGRATION_TESTS") != "true":
        pytest.skip("set RUN_INTEGRATION_TESTS=true to run service integration tests")

    from pymongo import MongoClient

    from backend.app import create_app
    from backend.app.config import Settings

    mongo_uri = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
    redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    database_name = f"caissa_rooms_{uuid.uuid4().hex}"
    settings = Settings(
        secret_key="integration-secret",
        mongo_uri=mongo_uri,
        mongo_database=database_name,
        redis_url=redis_url,
        host="127.0.0.1",
        port=5000,
        debug=False,
        environment="testing",
        allowed_origins=["http://localhost:5000"],
        testing=True,
    )
    mongo = MongoClient(mongo_uri)
    try:
        client = create_app(settings).test_client()
        assert (
            client.post(
                "/api/v1/auth/register",
                json={"username": "room_creator", "password": "correct horse battery"},
            ).status_code
            == 201
        )
        created = client.post("/api/v1/rooms", json={"name": "Persistent Room"})
        assert created.status_code == 201
        room_code = created.get_json()["room_code"]
        spectator = client.post(f"/api/v1/rooms/{room_code}/spectate")
        assert spectator.status_code == 200

        restarted = create_app(settings).test_client()
        room = restarted.get(f"/api/v1/rooms/{room_code}")
        assert room.status_code == 200
        assert room.get_json()["name"] == "Persistent Room"
        assert room.get_json()["spectator_count"] == 1
    finally:
        mongo.drop_database(database_name)
