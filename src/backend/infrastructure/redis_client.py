import redis


def get_redis_client(settings):
    client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    client.ping()
    return client
