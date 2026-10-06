import time


def presence_key(game_id: str, color: str) -> str:
    return f"presence:game:{game_id}:{color}"


def claim_presence(client, game_id: str, color: str, socket_id: str, ttl: int = 300):
    key = presence_key(game_id, color)
    previous = client.get(key)
    client.setex(key, ttl, socket_id)
    return previous


def release_presence(client, game_id: str, color: str, socket_id: str):
    key = presence_key(game_id, color)
    if client.get(key) == socket_id:
        client.delete(key)


class RedisRateLimiter:
    def __init__(self, client):
        self.client = client

    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        bucket = f"rate_limit:{key}:{int(time.time()) // window_seconds}"
        count = self.client.incr(bucket)
        if count == 1:
            self.client.expire(bucket, window_seconds)
        return count <= limit


class GameLock:
    def __init__(self, client, game_id: str, timeout: int = 5):
        self.client = client
        self.key = f"game_lock:{game_id}"
        self.timeout = timeout
        self.lock = None

    def __enter__(self):
        self.lock = self.client.lock(self.key, timeout=self.timeout, blocking_timeout=1)
        if not self.lock.acquire():
            raise TimeoutError("game is busy")
        return self

    def __exit__(self, _exc_type, _exc_value, _traceback):
        if self.lock:
            self.lock.release()
