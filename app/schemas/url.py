from datetime import datetime

from pydantic import BaseModel, HttpUrl, field_validator


class URLCreateRequest(BaseModel):
    url: HttpUrl
    custom_alias: str | None = None
    expires_in_days: int | None = None

    @field_validator("custom_alias")
    @classmethod
    def alias_must_be_alphanumeric(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Custom alias must be alphanumeric (hyphens and underscores allowed)")
        if len(v) < 3 or len(v) > 50:
            raise ValueError("Custom alias must be between 3 and 50 characters")
        return v.lower()


class URLResponse(BaseModel):
    short_url: str
    short_code: str
    original_url: str
    custom_alias: str | None
    click_count: int
    created_at: datetime
    expires_at: datetime | None

    model_config = {"from_attributes": True}


class URLInfoResponse(URLResponse):
    is_active: bool
    user_id: int | None