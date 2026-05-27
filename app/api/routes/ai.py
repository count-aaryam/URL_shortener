from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.ai import (
    AliasRequest,
    AliasResponse,
    MaliciousCheckRequest,
    MaliciousCheckResponse,
    UTMRequest,
    UTMResponse,
)
from app.services.ai import AIService

router = APIRouter(prefix="/ai")


def get_ai_service() -> AIService:
    return AIService()


@router.post("/suggest-alias", response_model=AliasResponse)
async def suggest_alias(
    payload: AliasRequest,
    service: AIService = Depends(get_ai_service),
    current_user: User = Depends(get_current_user),
):
    """Generate smart URL alias suggestions using AI."""
    try:
        suggestions = await service.suggest_aliases(
            url=str(payload.url),
            count=payload.count,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    return AliasResponse(url=str(payload.url), suggestions=suggestions)


@router.post("/detect-malicious", response_model=MaliciousCheckResponse)
async def detect_malicious(
    payload: MaliciousCheckRequest,
    service: AIService = Depends(get_ai_service),
    current_user: User = Depends(get_current_user),
):
    """Check if a URL is malicious or phishing using AI."""
    try:
        result = await service.check_malicious(url=str(payload.url))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    return MaliciousCheckResponse(
        url=str(payload.url),
        is_malicious=result["is_malicious"],
        confidence=result["confidence"],
        reasons=result["reasons"],
        recommendation=result["recommendation"],
    )


@router.post("/utm-tags", response_model=UTMResponse)
async def generate_utm_tags(
    payload: UTMRequest,
    service: AIService = Depends(get_ai_service),
    current_user: User = Depends(get_current_user),
):
    """Generate UTM campaign tracking tags using AI."""
    try:
        result = await service.generate_utm_tags(
            url=str(payload.url),
            campaign_goal=payload.campaign_goal,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    # Build the full tagged URL
    utm_params = {
        "utm_source": result["utm_source"],
        "utm_medium": result["utm_medium"],
        "utm_campaign": result["utm_campaign"],
        "utm_content": result["utm_content"],
        "utm_term": result["utm_term"],
    }
    separator = "&" if "?" in str(payload.url) else "?"
    tagged_url = f"{str(payload.url)}{separator}{urlencode(utm_params)}"

    return UTMResponse(
        original_url=str(payload.url),
        tagged_url=tagged_url,
        utm_params=utm_params,
        explanation=result["explanation"],
    )