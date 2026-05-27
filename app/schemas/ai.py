from pydantic import BaseModel, HttpUrl


class AliasRequest(BaseModel):
    url: HttpUrl
    count: int = 5  # number of suggestions to return


class AliasResponse(BaseModel):
    url: str
    suggestions: list[str]


class MaliciousCheckRequest(BaseModel):
    url: HttpUrl


class MaliciousCheckResponse(BaseModel):
    url: str
    is_malicious: bool
    confidence: str        # low / medium / high
    reasons: list[str]
    recommendation: str


class UTMRequest(BaseModel):
    url: HttpUrl
    campaign_goal: str     # e.g. "product launch", "newsletter", "social media"


class UTMResponse(BaseModel):
    original_url: str
    tagged_url: str
    utm_params: dict[str, str]
    explanation: str