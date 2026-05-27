import json
import logging
from typing import Optional

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

URL_CACHE_TTL = 60 * 60
NOT_FOUND_TTL = 60 * 5

URL_KEY_PREFIX = "url:"
NOT_FOUND_PREFIX = "url:404:"


class CacheService:

    def __init__(self, redis: Redis):
        self.redis = redis

    async def set_url(self, short_code: str, url_data: dict) -> None:
        key = self._url_key(short_code)
        try:
            await self.redis.setex(key, URL_CACHE_TTL, json.dumps(url_data))
        except Exception as e:
            logger.warning(f"Cache set failed for {short_code}: {e}")

    async def get_url(self, short_code: str) -> Optional[dict]:
        key = self._url_key(short_code)
        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Cache get failed for {short_code}: {e}")
        return None

    async def delete_url(self, short_code: str) -> None:
        try:
            await self.redis.delete(
                self._url_key(short_code),
                self._not_found_key(short_code),
            )
        except Exception as e:
            logger.warning(f"Cache delete failed for {short_code}: {e}")

    async def set_not_found(self, short_code: str) -> None:
        try:
            await self.redis.setex(self._not_found_key(short_code), NOT_FOUND_TTL, "1")
        except Exception as e:
            logger.warning(f"Cache set_not_found failed for {short_code}: {e}")

    async def is_not_found(self, short_code: str) -> bool:
        try:
            return await self.redis.exists(self._not_found_key(short_code)) == 1
        except Exception as e:
            logger.warning(f"Cache is_not_found failed for {short_code}: {e}")
        return False

    async def increment_click(self, short_code: str) -> None:
        try:
            await self.redis.incr(f"clicks:{short_code}")
        except Exception as e:
            logger.warning(f"Cache increment_click failed for {short_code}: {e}")

    async def ping(self) -> bool:
        try:
            return await self.redis.ping()
        except Exception:
            return False

    def _url_key(self, short_code: str) -> str:
        return f"{URL_KEY_PREFIX}{short_code}"

    def _not_found_key(self, short_code: str) -> str:
        return f"{NOT_FOUND_PREFIX}{short_code}"