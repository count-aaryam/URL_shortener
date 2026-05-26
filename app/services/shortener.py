from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.url import URL
from app.schemas.url import URLCreateRequest
from app.utils.base62 import generate_random_code

MAX_COLLISION_RETRIES = 5


class ShortenerService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_short_url(self, payload: URLCreateRequest) -> URL:
        original_url = str(payload.url)

        # Resolve short code: custom alias takes priority
        if payload.custom_alias:
            await self._assert_alias_available(payload.custom_alias)
            short_code = payload.custom_alias
        else:
            short_code = await self._generate_unique_code()

        # Resolve expiry
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
        await self.db.flush()  # get the ID before commit
        await self.db.refresh(url_obj)
        return url_obj

    async def resolve_short_code(self, short_code: str) -> URL | None:
        """Fetch URL by short code. Returns None if not found, inactive, or expired."""
        stmt = select(URL).where(URL.short_code == short_code, URL.is_active == True)
        result = await self.db.execute(stmt)
        url_obj = result.scalar_one_or_none()

        if url_obj is None:
            return None

        if url_obj.is_expired():
            return None

        # Increment click counter (fire-and-forget style for now; Phase 4 replaces this)
        url_obj.click_count += 1
        await self.db.flush()

        return url_obj

    async def get_url_info(self, short_code: str) -> URL | None:
        """Fetch URL metadata without incrementing click count."""
        stmt = select(URL).where(URL.short_code == short_code)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def deactivate_url(self, short_code: str) -> bool:
        url_obj = await self.get_url_info(short_code)
        if url_obj is None:
            return False
        url_obj.is_active = False
        await self.db.flush()
        return True

    # ── Private helpers ──────────────────────────────────────────────────────

    async def _generate_unique_code(self) -> str:
        """Generate a random code, retrying on collision (extremely rare)."""
        for _ in range(MAX_COLLISION_RETRIES):
            code = generate_random_code(settings.SHORT_CODE_LENGTH)
            if not await self._code_exists(code):
                return code
        raise RuntimeError("Failed to generate a unique short code after retries. Try again.")

    async def _code_exists(self, code: str) -> bool:
        stmt = select(URL.id).where(URL.short_code == code)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def _assert_alias_available(self, alias: str) -> None:
        stmt = select(URL.id).where(URL.short_code == alias)
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none() is not None:
            raise ValueError(f"Alias '{alias}' is already taken")
