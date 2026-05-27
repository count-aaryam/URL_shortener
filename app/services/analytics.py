from datetime import datetime, timezone

from sqlalchemy import func, select, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.click import Click
from app.models.url import URL
from app.schemas.analytics import (
    AnalyticsDetail,
    AnalyticsSummary,
    BrowserBreakdown,
    ClickEvent,
    ClicksOverTime,
    DeviceBreakdown,
    ReferrerBreakdown,
)

try:
    from user_agents import parse as parse_ua
    UA_AVAILABLE = True
except ImportError:
    UA_AVAILABLE = False


class AnalyticsService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_click(
        self,
        url_id: int,
        short_code: str,
        ip_address: str | None,
        user_agent_str: str | None,
        referrer: str | None,
    ) -> None:
        """Parse request metadata and store click event."""
        device_type = None
        browser = None
        os = None

        if user_agent_str and UA_AVAILABLE:
            ua = parse_ua(user_agent_str)
            browser = ua.browser.family
            os = ua.os.family
            if ua.is_mobile:
                device_type = "mobile"
            elif ua.is_tablet:
                device_type = "tablet"
            else:
                device_type = "desktop"

        click = Click(
            url_id=url_id,
            short_code=short_code,
            ip_address=ip_address,
            user_agent=user_agent_str,
            referrer=referrer,
            device_type=device_type,
            browser=browser,
            os=os,
        )

        self.db.add(click)
        await self.db.flush()

    async def get_summary(self, short_code: str) -> AnalyticsSummary | None:
        """Get aggregated analytics for a short code."""

        # Get URL info
        url_stmt = select(URL).where(URL.short_code == short_code)
        url_result = await self.db.execute(url_stmt)
        url_obj = url_result.scalar_one_or_none()
        if url_obj is None:
            return None

        # Total clicks
        total_stmt = select(func.count(Click.id)).where(Click.short_code == short_code)
        total = (await self.db.execute(total_stmt)).scalar() or 0

        # Unique IPs
        unique_stmt = select(func.count(distinct(Click.ip_address))).where(
            Click.short_code == short_code
        )
        unique_ips = (await self.db.execute(unique_stmt)).scalar() or 0

        # Device breakdown
        device_stmt = (
            select(Click.device_type, func.count(Click.id).label("count"))
            .where(Click.short_code == short_code, Click.device_type.isnot(None))
            .group_by(Click.device_type)
            .order_by(func.count(Click.id).desc())
        )
        device_rows = (await self.db.execute(device_stmt)).fetchall()
        devices = [DeviceBreakdown(device_type=r[0], count=r[1]) for r in device_rows]

        # Browser breakdown
        browser_stmt = (
            select(Click.browser, func.count(Click.id).label("count"))
            .where(Click.short_code == short_code, Click.browser.isnot(None))
            .group_by(Click.browser)
            .order_by(func.count(Click.id).desc())
            .limit(5)
        )
        browser_rows = (await self.db.execute(browser_stmt)).fetchall()
        browsers = [BrowserBreakdown(browser=r[0], count=r[1]) for r in browser_rows]

        # Top referrers
        referrer_stmt = (
            select(Click.referrer, func.count(Click.id).label("count"))
            .where(Click.short_code == short_code, Click.referrer.isnot(None))
            .group_by(Click.referrer)
            .order_by(func.count(Click.id).desc())
            .limit(5)
        )
        referrer_rows = (await self.db.execute(referrer_stmt)).fetchall()
        referrers = [ReferrerBreakdown(referrer=r[0], count=r[1]) for r in referrer_rows]

        # Clicks over time (daily for last 30 days)
        time_stmt = (
            select(
                func.date(Click.clicked_at).label("date"),
                func.count(Click.id).label("count"),
            )
            .where(Click.short_code == short_code)
            .group_by(func.date(Click.clicked_at))
            .order_by(func.date(Click.clicked_at))
        )
        time_rows = (await self.db.execute(time_stmt)).fetchall()
        clicks_over_time = [
            ClicksOverTime(date=str(r[0]), count=r[1]) for r in time_rows
        ]

        return AnalyticsSummary(
            short_code=short_code,
            original_url=url_obj.original_url,
            total_clicks=total,
            unique_ips=unique_ips,
            devices=devices,
            browsers=browsers,
            top_referrers=referrers,
            clicks_over_time=clicks_over_time,
            created_at=url_obj.created_at,
        )

    async def get_detail(self, short_code: str, limit: int = 50) -> AnalyticsDetail | None:
        """Get summary + recent individual click events."""
        summary = await self.get_summary(short_code)
        if summary is None:
            return None

        recent_stmt = (
            select(Click)
            .where(Click.short_code == short_code)
            .order_by(Click.clicked_at.desc())
            .limit(limit)
        )
        recent_result = await self.db.execute(recent_stmt)
        recent_clicks = [
            ClickEvent.model_validate(c) for c in recent_result.scalars().all()
        ]

        return AnalyticsDetail(summary=summary, recent_clicks=recent_clicks)