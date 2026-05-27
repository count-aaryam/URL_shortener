from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.url import URL
from app.schemas.url import URLCreateRequest
from app.services.cache import CacheService
from app.utils.base62 import generate_random_code

MAX_COLLISION_RETRIES = 5


class ShortenerService:

    def __init__(self, db: AsyncSession, cache: CacheService):
        self.db = db
        self.cache = cache

    async def create_short_url(self, payload: URLCreateRequest) -> URL:
        original_url = str(payload.url)

        if payload.custom_alias:
            await self._assert_alias_available(payload.custom_alias)
            short_code = payload.custom_alias
        else:
            short_code = await self._generate_unique_code()

        expires_at = None
        if payload.expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)

        url_obj = URL(
            original_url=original_url,
            short_code=short_code,
            custom_alias=payload.custom_alias,
            expires_at=expires_at,
        )

        self.db.add(url_obj)
        await self.db.flush()
        await self.db.refresh(url_obj)

        # Warm cache immediately after creation
        await self.cache.set_url(short_code, self._serialize(url_obj))

        return url_obj

    async def resolve_short_code(self, short_code: str) -> URL | None:
        """
        Cache-first lookup:
        1. Negative cache check  → return None instantly
        2. Redis cache hit       → return instantly
        3. PostgreSQL fallback   → populate cache → return
        """

        # 1. Negative cache — previously confirmed not found
        if await self.cache.is_not_found(short_code):
            return None

        # 2. Redis hit
        cached = await self.cache.get_url(short_code)
        if cached:
            await self.cache.increment_click(short_code)
            return self._deserialize(cached)

        # 3. PostgreSQL fallback
        stmt = select(URL).where(URL.short_code == short_code, URL.is_active == True)
        result = await self.db.execute(stmt)
        url_obj = result.scalar_one_or_none()

        if url_obj is None or url_obj.is_expired():
            await self.cache.set_not_found(short_code)
            return None

        # Populate cache for next request
        await self.cache.set_url(short_code, self._serialize(url_obj))

        # Increment in DB (Phase 4 moves this to async queue)
        url_obj.click_count += 1
        await self.db.flush()

        return url_obj

    async def get_url_info(self, short_code: str) -> URL | None:
        stmt = select(URL).where(URL.short_code == short_code)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def deactivate_url(self, short_code: str) -> bool:
        url_obj = await self.get_url_info(short_code)
        if url_obj is None:
            return False
        url_obj.is_active = False
        await self.db.flush()
        await self.cache.delete_url(short_code)
        return True

    # ── Serialization ────────────────────────────────────────────────────────

    def _serialize(self, url_obj: URL) -> dict:
        return {
            "id": url_obj.id,
            "original_url": url_obj.original_url,
            "short_code": url_obj.short_code,
            "custom_alias": url_obj.custom_alias,
            "user_id": url_obj.user_id,
            "click_count": url_obj.click_count,
            "is_active": url_obj.is_active,
            "expires_at": url_obj.expires_at.isoformat() if url_obj.expires_at else None,
            "created_at": url_obj.created_at.isoformat(),
            "updated_at": url_obj.updated_at.isoformat(),
        }

    def _deserialize(self, data: dict) -> URL:
        return URL(
            id=data["id"],
            original_url=data["original_url"],
            short_code=data["short_code"],
            custom_alias=data["custom_alias"],
            user_id=data["user_id"],
            click_count=data["click_count"],
            is_active=data["is_active"],
            expires_at=datetime.fromisoformat(data["expires_at"]) if data["expires_at"] else None,
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )

    # ── Private helpers ──────────────────────────────────────────────────────

    async def _generate_unique_code(self) -> str:
        for _ in range(MAX_COLLISION_RETRIES):
            code = generate_random_code(settings.SHORT_CODE_LENGTH)
            if not await self._code_exists(code):
                return code
        raise RuntimeError("Failed to generate unique short code after retries.")

    async def _code_exists(self, code: str) -> bool:
        stmt = select(URL.id).where(URL.short_code == code)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def _assert_alias_available(self, alias: str) -> None:
        stmt = select(URL.id).where(URL.short_code == alias)
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none() is not None:
            raise ValueError(f"Alias '{alias}' is already taken")