from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.analytics import AnalyticsDetail, AnalyticsSummary
from app.services.analytics import AnalyticsService
from app.services.shortener import ShortenerService
from app.services.cache import CacheService
from app.core.redis import get_redis_client
from redis.asyncio import Redis

router = APIRouter(prefix="/analytics")


def get_analytics_service(db: AsyncSession = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(db=db)


@router.get("/{short_code}/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    short_code: str,
    service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(get_current_user),
):
    # Verify ownership
    db = service.db
    from app.models.url import URL
    from sqlalchemy import select
    stmt = select(URL).where(URL.short_code == short_code)
    result = await db.execute(stmt)
    url_obj = result.scalar_one_or_none()

    if url_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found")
    if url_obj.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your link")

    summary = await service.get_summary(short_code)
    return summary


@router.get("/{short_code}", response_model=AnalyticsDetail)
async def get_analytics_detail(
    short_code: str,
    service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(get_current_user),
):
    # Verify ownership
    db = service.db
    from app.models.url import URL
    from sqlalchemy import select
    stmt = select(URL).where(URL.short_code == short_code)
    result = await db.execute(stmt)
    url_obj = result.scalar_one_or_none()

    if url_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found")
    if url_obj.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your link")

    detail = await service.get_detail(short_code)
    return detail

@router.post("/admin/cleanup", tags=["Admin"])
async def trigger_cleanup(
    current_user: User = Depends(get_current_user),
):
    """Manually trigger expired URL cleanup — for testing."""
    from app.services.cleanup import cleanup_expired_urls
    await cleanup_expired_urls()
    return {"status": "cleanup triggered"}