import logging
from redis.asyncio import Redis, ConnectionPool
from app.config import settings

logger = logging.getLogger(__name__)

_pool: ConnectionPool | None = None
_redis: Redis | None = None


def get_redis_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=20,
            decode_responses=True,
        )
    return _pool


def get_redis_client() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis(connection_pool=get_redis_pool())
    return _redis


async def close_redis():
    global _redis, _pool
    if _redis:
        await _redis.aclose()
        _redis = None
    if _pool:
        await _pool.aclose()
        _pool = None