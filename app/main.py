from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import url as url_router
from app.config import settings
from app.core.redis import close_redis, get_redis_client
from app.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    redis = get_redis_client()
    if await redis.ping():
        print("✓ Redis connected")
    else:
        print("✗ Redis connection failed — redirects will fall back to DB")

    yield

    # Shutdown
    await close_redis()
    await engine.dispose()


app = FastAPI(
    title="URL Shortener API",
    description="A scalable URL shortening system with Redis caching.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/health", tags=["Health"])
async def health_check():
    redis = get_redis_client()
    redis_ok = await redis.ping()
    return {
        "status": "ok",
        "env": settings.APP_ENV,
        "redis": "connected" if redis_ok else "disconnected",
    }

app.include_router(url_router.router, tags=["URL Shortener"],prefix="/api")
