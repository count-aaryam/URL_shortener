from datetime import datetime

from pydantic import BaseModel


class ClickEvent(BaseModel):
    id: int
    short_code: str
    ip_address: str | None
    referrer: str | None
    device_type: str | None
    browser: str | None
    os: str | None
    country: str | None
    clicked_at: datetime

    model_config = {"from_attributes": True}


class DeviceBreakdown(BaseModel):
    device_type: str
    count: int


class BrowserBreakdown(BaseModel):
    browser: str
    count: int


class ReferrerBreakdown(BaseModel):
    referrer: str
    count: int


class ClicksOverTime(BaseModel):
    date: str
    count: int


class AnalyticsSummary(BaseModel):
    short_code: str
    original_url: str
    total_clicks: int
    unique_ips: int
    devices: list[DeviceBreakdown]
    browsers: list[BrowserBreakdown]
    top_referrers: list[ReferrerBreakdown]
    clicks_over_time: list[ClicksOverTime]
    created_at: datetime


class AnalyticsDetail(BaseModel):
    summary: AnalyticsSummary
    recent_clicks: list[ClickEvent]