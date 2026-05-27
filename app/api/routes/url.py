from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import get_current_user, get_optional_user
from app.core.redis import get_redis_client
from app.database import get_db
from app.models.url import URL
from app.models.user import User
from app.schemas.url import URLCreateRequest, URLInfoResponse, URLResponse
from app.services.cache import CacheService
from app.services.shortener import ShortenerService

router = APIRouter()


def get_service(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_client),
) -> ShortenerService:
    return ShortenerService(db=db, cache=CacheService(redis=redis))


@router.post("/shorten", response_model=URLResponse, status_code=status.HTTP_201_CREATED)
async def shorten_url(
    payload: URLCreateRequest,
    service: ShortenerService = Depends(get_service),
    current_user: User = Depends(get_current_user),  # ← auth required
):
    try:
        url_obj = await service.create_short_url(payload, user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return URLResponse(
        short_url=f"{settings.APP_BASE_URL}/{url_obj.short_code}",
        short_code=url_obj.short_code,
        original_url=url_obj.original_url,
        custom_alias=url_obj.custom_alias,
        click_count=url_obj.click_count,
        created_at=url_obj.created_at,
        expires_at=url_obj.expires_at,
    )


@router.get("/my-urls", response_model=list[URLResponse])
async def get_my_urls(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(URL).where(URL.user_id == current_user.id).order_by(URL.created_at.desc())
    result = await db.execute(stmt)
    urls = result.scalars().all()

    return [
        URLResponse(
            short_url=f"{settings.APP_BASE_URL}/{u.short_code}",
            short_code=u.short_code,
            original_url=u.original_url,
            custom_alias=u.custom_alias,
            click_count=u.click_count,
            created_at=u.created_at,
            expires_at=u.expires_at,
        )
        for u in urls
    ]


@router.get("/info/{short_code}", response_model=URLInfoResponse)
async def get_url_info(
    short_code: str,
    service: ShortenerService = Depends(get_service),
):
    url_obj = await service.get_url_info(short_code)
    if url_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found")

    return URLInfoResponse(
        short_url=f"{settings.APP_BASE_URL}/{url_obj.short_code}",
        short_code=url_obj.short_code,
        original_url=url_obj.original_url,
        custom_alias=url_obj.custom_alias,
        click_count=url_obj.click_count,
        created_at=url_obj.created_at,
        expires_at=url_obj.expires_at,
        is_active=url_obj.is_active,
        user_id=url_obj.user_id,
    )


@router.delete("/{short_code}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_url(
    short_code: str,
    service: ShortenerService = Depends(get_service),
    current_user: User = Depends(get_current_user),
):
    url_obj = await service.get_url_info(short_code)

    if url_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found")

    # Only owner can deactivate
    if url_obj.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your link")

    await service.deactivate_url(short_code)


# ── Redirect — no auth required, MUST be last ────────────────────────────────

@router.get("/{short_code}")
async def redirect_to_url(
    short_code: str,
    request: Request,
    service: ShortenerService = Depends(get_service),
):
    url_obj = await service.resolve_short_code(short_code)
    if url_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short URL not found or has expired",
        )
    return RedirectResponse(url=url_obj.original_url, status_code=status.HTTP_302_FOUND)