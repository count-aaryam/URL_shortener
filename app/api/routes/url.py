from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.schemas.url import URLCreateRequest, URLInfoResponse, URLResponse
from app.services.shortener import ShortenerService

router = APIRouter()


@router.post("/shorten", response_model=URLResponse, status_code=status.HTTP_201_CREATED)
async def shorten_url(
    payload: URLCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    service = ShortenerService(db)

    try:
        url_obj = await service.create_short_url(payload)
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


@router.get("/info/{short_code}", response_model=URLInfoResponse)
async def get_url_info(
    short_code: str,
    db: AsyncSession = Depends(get_db),
):
    service = ShortenerService(db)
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
    db: AsyncSession = Depends(get_db),
):
    service = ShortenerService(db)
    deleted = await service.deactivate_url(short_code)

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found")


# ── Redirect — MUST be last to avoid shadowing other routes ─────────────────

@router.get("/{short_code}")
async def redirect_to_url(
    short_code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    service = ShortenerService(db)
    url_obj = await service.resolve_short_code(short_code)

    if url_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short URL not found or has expired",
        )

    return RedirectResponse(url=url_obj.original_url, status_code=status.HTTP_302_FOUND)