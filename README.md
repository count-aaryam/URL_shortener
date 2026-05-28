# ⚡ SwiftURL — Production-Grade URL Shortener

> A scalable, high-performance URL shortening system built with FastAPI, PostgreSQL, and Redis — featuring sub-millisecond redirects, real-time click analytics, JWT authentication, background job scheduling, and AI-powered link intelligence.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [System Architecture](#system-architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Docker Setup](#docker-setup)
- [API Reference](#api-reference)
- [Usage Examples](#usage-examples)
- [Database Schema](#database-schema)
- [Key Design Decisions](#key-design-decisions)
- [Performance](#performance)
- [Security](#security)
- [Background Jobs](#background-jobs)
- [AI Features](#ai-features)
- [Roadmap](#roadmap)
- [Contributing](#contributing)

---

## Overview

SwiftURL is a full-featured URL shortening backend system inspired by Bitly. It was built from scratch as a backend engineering project to demonstrate real-world production patterns including caching, async database access, authentication, analytics pipelines, background jobs, and AI integration.

The system handles the complete lifecycle of a short URL:

```
User submits long URL
        ↓
Backend validates URL
        ↓
Generates Base62 short code (7 chars = 3.5 trillion combinations)
        ↓
Stores mapping in PostgreSQL
        ↓
Warms Redis cache immediately
        ↓
Returns short URL to user

When someone clicks:
        ↓
Short code received
        ↓
Redis cache checked first (<1ms on hit)
        ↓
PostgreSQL fallback on cache miss
        ↓
302 Redirect fired
        ↓
Click event logged asynchronously (IP, device, browser, referrer)
```

---

## Features

### Core
- **Base62 URL shortening** — 7-character codes with 3.5 trillion possible combinations
- **Custom aliases** — vanity URLs like `sho.rt/my-github`
- **Link expiry** — set expiry dates, auto-cleanup via background jobs
- **Soft deletes** — links deactivated not destroyed, preserving analytics history
- **Collision handling** — retry loop with up to 5 attempts on the rare collision

### Performance
- **Sub-millisecond redirects** — Redis cache serves repeat hits in under 1ms
- **Cache warming** — new URLs written to Redis immediately on creation
- **Negative caching** — invalid codes cached for 5 minutes, preventing repeated DB hits
- **Async throughout** — non-blocking DB, cache, and HTTP operations from top to bottom
- **Connection pooling** — PostgreSQL pool (10 connections, 20 overflow) and Redis pool (20 connections)

### Authentication
- **JWT-based auth** — 24-hour access tokens
- **bcrypt password hashing** — secure credential storage
- **Ownership enforcement** — users can only modify their own links
- **Optional auth** — redirect endpoint works without auth, protected endpoints require it

### Analytics
- **Per-click tracking** — every redirect logged with full metadata
- **Device detection** — mobile/tablet/desktop via User-Agent parsing
- **Browser and OS tracking** — Chrome, Safari, Firefox, Windows, iOS, Android etc
- **Referrer tracking** — see where your traffic comes from
- **IP tracking** — unique visitor counting
- **Time-series data** — clicks aggregated by day for trend analysis
- **Top referrers** — ranked list of traffic sources

### AI (OpenAI GPT-3.5-turbo)
- **Smart alias suggestions** — AI reads URL content and suggests meaningful short codes
- **Malicious URL detection** — AI analyzes URLs for phishing, typosquatting, and spam patterns
- **UTM tag generation** — AI generates complete campaign tracking parameters for marketing

### Background Jobs
- **Hourly expiry cleanup** — expired links deactivated and removed from Redis
- **Weekly click pruning** — click events older than 90 days deleted to keep DB lean
- **Graceful lifecycle** — scheduler starts and stops cleanly with app lifecycle

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Request                        │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Backend (Uvicorn ASGI)                  │
│                                                              │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│   │  Auth Routes │  │  URL Routes  │  │ Analytics Routes │ │
│   └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘ │
│          │                 │                    │           │
│   ┌──────▼─────────────────▼────────────────────▼────────┐ │
│   │              Service Layer                            │ │
│   │  AuthService │ ShortenerService │ AnalyticsService   │ │
│   └──────┬───────────────┬──────────────────┬────────────┘ │
│          │               │                  │              │
│   ┌──────▼──────┐  ┌─────▼──────┐   ┌──────▼───────────┐ │
│   │  PostgreSQL │  │   Redis    │   │   APScheduler    │ │
│   │  (Primary)  │  │  (Cache)   │   │ (Background Jobs)│ │
│   └─────────────┘  └────────────┘   └──────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Redirect Flow (Critical Path)

```
GET /{short_code}
        │
        ▼
Negative cache check ──── HIT ──→ Return 404 instantly
        │
       MISS
        │
        ▼
Redis cache lookup ──────── HIT ──→ Increment click → Return 302
        │
       MISS
        │
        ▼
PostgreSQL lookup
        │
     Not found ──────────────────→ Cache miss → Return 404
        │
      Found
        │
        ▼
Populate Redis cache
        │
        ▼
Increment click count
        │
        ▼
Log click event (device, IP, referrer)
        │
        ▼
Return 302 Redirect
```

---

## Tech Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Language** | Python | 3.13 | Core runtime |
| **Framework** | FastAPI | 0.115.0 | Async web framework |
| **Server** | Uvicorn | 0.30.6 | ASGI server |
| **Database** | PostgreSQL | 17 | Primary data store |
| **ORM** | SQLAlchemy | 2.0.35 | Async database access |
| **DB Driver** | asyncpg | 0.30.0 | Async PostgreSQL driver |
| **Cache** | Redis | 7 | Sub-millisecond caching |
| **Redis Client** | redis-py | 5.0.8 | Async Redis client |
| **Migrations** | Alembic | 1.13.3 | Database schema versioning |
| **Validation** | Pydantic | 2.9.2 | Request/response validation |
| **Auth** | python-jose | 3.3.0 | JWT token handling |
| **Hashing** | bcrypt | 4.2.0 | Password hashing |
| **Scheduler** | APScheduler | 3.10.4 | Background job scheduling |
| **AI** | OpenAI | 1.30.1 | GPT-3.5-turbo integration |
| **UA Parsing** | user-agents | 2.2.0 | Device/browser detection |
| **Containerization** | Docker | — | Deployment containerization |

---

## Project Structure

```
url-shortener/
├── app/
│   ├── main.py                    # FastAPI app, middleware, router registration, lifespan
│   ├── config.py                  # Centralized config via pydantic-settings + .env
│   ├── database.py                # Async SQLAlchemy engine, session factory, Base
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── redis.py               # Redis connection pool — singleton pattern
│   │   ├── security.py            # JWT encode/decode, bcrypt hash/verify
│   │   ├── dependencies.py        # get_current_user, get_optional_user FastAPI deps
│   │   └── scheduler.py           # APScheduler setup and job registration
│   │
│   ├── models/
│   │   ├── __init__.py            # Imports all models for Alembic detection
│   │   ├── url.py                 # URL SQLAlchemy model (urls table)
│   │   ├── user.py                # User SQLAlchemy model (users table)
│   │   └── click.py               # Click SQLAlchemy model (clicks table)
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── url.py                 # URLCreateRequest, URLResponse, URLInfoResponse
│   │   ├── user.py                # UserRegisterRequest, UserLoginRequest, TokenResponse
│   │   ├── analytics.py           # AnalyticsSummary, AnalyticsDetail, ClickEvent
│   │   └── ai.py                  # AliasRequest/Response, MaliciousCheck, UTMRequest
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── shortener.py           # create_short_url, resolve_short_code, deactivate
│   │   ├── cache.py               # set_url, get_url, delete_url, negative caching
│   │   ├── auth.py                # register, login, get_user_by_id
│   │   ├── analytics.py           # log_click, get_summary, get_detail
│   │   ├── cleanup.py             # cleanup_expired_urls, cleanup_old_clicks
│   │   └── ai.py                  # suggest_aliases, check_malicious, generate_utm_tags
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── url.py             # POST /shorten, GET /{code}, GET /my-urls, DELETE
│   │       ├── auth.py            # POST /register, POST /login, GET /me
│   │       ├── analytics.py       # GET /analytics/{code}, GET /analytics/{code}/summary
│   │       └── ai.py              # POST /ai/suggest-alias, /detect-malicious, /utm-tags
│   │
│   └── utils/
│       ├── __init__.py
│       └── base62.py              # encode(), decode(), generate_random_code()
│
├── alembic/
│   ├── env.py                     # Async Alembic config — reads from .env
│   ├── script.py.mako
│   └── versions/                  # Auto-generated migration files
│
├── alembic.ini                    # Alembic configuration
├── requirements.txt               # All Python dependencies
├── Dockerfile                     # Container definition
├── docker-compose.yml             # Full stack orchestration
├── .env                           # Local secrets — never committed
├── .env.example                   # Template for .env — committed
├── .gitignore
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.11 or higher
- PostgreSQL 15 or higher
- Redis 7 or higher
- Git

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/url-shortener.git
cd url-shortener
```

### 2. Create virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:yourpassword@localhost:5432/urlshortener

# Redis
REDIS_URL=redis://localhost:6379/0

# App
APP_BASE_URL=http://localhost:8000/api
APP_ENV=development
SHORT_CODE_LENGTH=7

# Auth
JWT_SECRET=your-super-secret-key-minimum-32-chars
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# AI (optional)
OPENAI_API_KEY=sk-proj-your-key-here
```

### 5. Create the database

```bash
# Using psql
psql -U postgres -c "CREATE DATABASE urlshortener;"

# Or using pgAdmin — right click Databases → Create → Database → name it urlshortener
```

### 6. Run migrations

```bash
alembic upgrade head
```

### 7. Start Redis

```bash
# WSL (Ubuntu)
sudo service redis-server start

# Verify
redis-cli ping   # should return PONG
```

### 8. Start the server

```bash
uvicorn app.main:app --reload
```

You should see:
```
✓ Redis connected
✓ Scheduler started
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### 9. Explore the API

Open `http://localhost:8000/docs` for the interactive Swagger UI.

---

## Docker Setup

Run the entire stack — FastAPI, PostgreSQL, and Redis — with a single command:

```bash
docker-compose up --build
```

Services:
- FastAPI app → `http://localhost:8000`
- PostgreSQL → `localhost:5432`
- Redis → `localhost:6379`

Stop everything:
```bash
docker-compose down
```

Stop and remove all data:
```bash
docker-compose down -v
```

---

## API Reference

All endpoints are prefixed with `/api`. Authentication uses Bearer tokens in the `Authorization` header.

### 🔐 Authentication

| Method | Endpoint | Auth | Description |
|--------|---------|------|-------------|
| `POST` | `/api/auth/register` | ❌ | Create new account. Returns JWT token + user info |
| `POST` | `/api/auth/login` | ❌ | Login with email/password. Returns JWT token |
| `GET` | `/api/auth/me` | ✅ | Get current authenticated user info |

**Register request:**
```json
{
  "email": "user@example.com",
  "username": "myusername",
  "password": "password123"
}
```

**Login response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "myusername",
    "is_active": true,
    "created_at": "2026-05-27T10:00:00Z"
  }
}
```

---

### 🔗 URL Shortener

| Method | Endpoint | Auth | Description |
|--------|---------|------|-------------|
| `POST` | `/api/shorten` | ✅ | Create a short URL |
| `GET` | `/api/{short_code}` | ❌ | Redirect to original URL (302) |
| `GET` | `/api/info/{short_code}` | ❌ | Get URL metadata without redirecting |
| `GET` | `/api/my-urls` | ✅ | Get all links created by current user |
| `DELETE` | `/api/{short_code}` | ✅ | Deactivate a link (owner only) |

**Shorten request:**
```json
{
  "url": "https://verylongwebsite.com/product/details?id=9283",
  "custom_alias": "my-product",
  "expires_in_days": 30
}
```

**Shorten response:**
```json
{
  "short_url": "http://localhost:8000/api/my-product",
  "short_code": "my-product",
  "original_url": "https://verylongwebsite.com/product/details?id=9283",
  "custom_alias": "my-product",
  "click_count": 0,
  "created_at": "2026-05-27T10:00:00Z",
  "expires_at": "2026-06-26T10:00:00Z"
}
```

---

### 📊 Analytics

| Method | Endpoint | Auth | Description |
|--------|---------|------|-------------|
| `GET` | `/api/analytics/{short_code}/summary` | ✅ | Aggregated click statistics |
| `GET` | `/api/analytics/{short_code}` | ✅ | Full detail with recent 50 click events |
| `POST` | `/api/analytics/admin/cleanup` | ✅ | Manually trigger expired link cleanup |

**Summary response:**
```json
{
  "short_code": "my-product",
  "original_url": "https://verylongwebsite.com/...",
  "total_clicks": 142,
  "unique_ips": 89,
  "devices": [
    {"device_type": "desktop", "count": 98},
    {"device_type": "mobile", "count": 44}
  ],
  "browsers": [
    {"browser": "Chrome", "count": 87},
    {"browser": "Safari", "count": 55}
  ],
  "top_referrers": [
    {"referrer": "https://twitter.com", "count": 60},
    {"referrer": "https://linkedin.com", "count": 42}
  ],
  "clicks_over_time": [
    {"date": "2026-05-25", "count": 45},
    {"date": "2026-05-26", "count": 61},
    {"date": "2026-05-27", "count": 36}
  ],
  "created_at": "2026-05-25T08:00:00Z"
}
```

---

### 🤖 AI Features

| Method | Endpoint | Auth | Description |
|--------|---------|------|-------------|
| `POST` | `/api/ai/suggest-alias` | ✅ | Generate smart alias suggestions from URL |
| `POST` | `/api/ai/detect-malicious` | ✅ | Detect phishing or malicious URLs |
| `POST` | `/api/ai/utm-tags` | ✅ | Generate UTM campaign tracking tags |

**Suggest alias request:**
```json
{
  "url": "https://amazon.com/product/iphone-15-pro-max",
  "count": 5
}
```

**Suggest alias response:**
```json
{
  "url": "https://amazon.com/product/iphone-15-pro-max",
  "suggestions": ["iphone-15-pro", "apple-iphone", "iphone-deal", "new-iphone", "iphone-max"]
}
```

**Malicious check request:**
```json
{
  "url": "https://paypa1-secure-login.xyz/account/verify"
}
```

**Malicious check response:**
```json
{
  "url": "https://paypa1-secure-login.xyz/account/verify",
  "is_malicious": true,
  "confidence": "high",
  "reasons": [
    "Typosquatting of 'paypal' — uses '1' instead of 'l'",
    "Suspicious TLD (.xyz) commonly used in phishing",
    "Path pattern matches credential harvesting pages"
  ],
  "recommendation": "Do not visit this URL. It is likely a phishing attempt impersonating PayPal."
}
```

**UTM tags request:**
```json
{
  "url": "https://mystore.com/summer-sale",
  "campaign_goal": "summer sale email newsletter"
}
```

**UTM tags response:**
```json
{
  "original_url": "https://mystore.com/summer-sale",
  "tagged_url": "https://mystore.com/summer-sale?utm_source=newsletter&utm_medium=email&utm_campaign=summer-sale-2026&utm_content=cta-button&utm_term=summer-deals",
  "utm_params": {
    "utm_source": "newsletter",
    "utm_medium": "email",
    "utm_campaign": "summer-sale-2026",
    "utm_content": "cta-button",
    "utm_term": "summer-deals"
  },
  "explanation": "Source set to newsletter since this is an email campaign. Medium is email. Campaign name reflects the summer sale with year for tracking."
}
```

---

### 🩺 System

| Method | Endpoint | Description |
|--------|---------|-------------|
| `GET` | `/health` | Returns server status + Redis connection state |

**Health response:**
```json
{
  "status": "ok",
  "env": "development",
  "redis": "connected",
  "scheduler": "running"
}
```

---

## Usage Examples

### Full flow with curl

```bash
# 1. Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "username": "myuser", "password": "password123"}'

# 2. Login and save token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}' \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# 3. Shorten a URL
curl -X POST http://localhost:8000/api/shorten \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com/yourusername", "custom_alias": "my-github"}'

# 4. Use the short link
curl -L http://localhost:8000/api/my-github

# 5. Check analytics
curl http://localhost:8000/api/analytics/my-github/summary \
  -H "Authorization: Bearer $TOKEN"
```

---

## Database Schema

### `users`

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | INTEGER | PK, autoincrement | Primary key |
| email | VARCHAR(255) | UNIQUE, NOT NULL, indexed | User email address |
| username | VARCHAR(50) | UNIQUE, NOT NULL, indexed | Display username |
| hashed_password | VARCHAR(255) | NOT NULL | bcrypt hash |
| is_active | BOOLEAN | NOT NULL, default true | Account status |
| is_verified | BOOLEAN | NOT NULL, default false | Email verification |
| created_at | TIMESTAMPTZ | NOT NULL | Creation timestamp |
| updated_at | TIMESTAMPTZ | NOT NULL | Last update timestamp |

### `urls`

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | INTEGER | PK, autoincrement | Primary key |
| original_url | TEXT | NOT NULL | The long URL |
| short_code | VARCHAR(20) | UNIQUE, NOT NULL, indexed | Generated or custom code |
| custom_alias | VARCHAR(50) | UNIQUE, nullable | Vanity alias |
| user_id | INTEGER | FK → users.id, indexed | Owner |
| expires_at | TIMESTAMPTZ | nullable | Optional expiry |
| is_active | BOOLEAN | NOT NULL, default true | Soft delete flag |
| click_count | INTEGER | NOT NULL, default 0 | Total redirect count |
| created_at | TIMESTAMPTZ | NOT NULL | Creation timestamp |
| updated_at | TIMESTAMPTZ | NOT NULL | Last update timestamp |

### `clicks`

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | INTEGER | PK, autoincrement | Primary key |
| url_id | INTEGER | FK → urls.id CASCADE, indexed | Parent URL |
| short_code | VARCHAR(20) | NOT NULL, indexed | For fast lookups |
| ip_address | VARCHAR(45) | nullable | IPv4 or IPv6 |
| user_agent | TEXT | nullable | Raw User-Agent string |
| referrer | TEXT | nullable | HTTP Referer header |
| device_type | VARCHAR(20) | nullable | mobile/tablet/desktop |
| browser | VARCHAR(50) | nullable | Chrome/Safari/Firefox etc |
| os | VARCHAR(50) | nullable | Windows/macOS/iOS/Android |
| country | VARCHAR(100) | nullable | Geo lookup (future) |
| clicked_at | TIMESTAMPTZ | NOT NULL, indexed | Event timestamp |

---

## Key Design Decisions

### Async from day one
SQLAlchemy 2.0 async with asyncpg driver means zero blocking operations anywhere in the stack. Every DB call, cache call, and HTTP request is non-blocking. This was a deliberate choice made in Phase 1 so nothing needed to be refactored as the system grew.

### Cache-first redirects
The redirect endpoint — the highest-traffic route in the system — never hits PostgreSQL on a repeat request. The first hit queries the DB and populates Redis. Every subsequent hit returns in under 1ms directly from Redis. On cache miss (expired TTL), the DB is queried and the cache is repopulated.

### 302 over 301 redirects
301 (permanent) redirects get cached by browsers indefinitely. Once a browser caches a 301, future clicks never reach the server — making analytics completely inaccurate. 302 (temporary) forces every click through the server, ensuring all analytics events are captured.

### Negative caching
When a short code doesn't exist in the DB, that result is cached in Redis for 5 minutes under a `url:404:` prefix. This prevents bot traffic and typos from hammering PostgreSQL with lookups that will never return results.

### Soft deletes
Links are never `DELETE`d from the database. Setting `is_active = False` preserves the complete click history for that link, prevents accidental data loss, and allows recovery. The cache is invalidated immediately on deactivation.

### Random codes over sequential IDs
`generate_random_code(7)` produces a random Base62 string rather than encoding the database row ID. Sequential IDs (`abc1`, `abc2`, `abc3`) expose your total link volume publicly — any competitor can see you've created 47 links. Random codes reveal nothing.

### Service layer isolation
Route handlers never import SQLAlchemy or touch the database directly. All business logic lives in service classes (`ShortenerService`, `AuthService`, `AnalyticsService`). Routes only handle HTTP concerns — parsing requests and forming responses. This makes the business logic independently testable.

### URL router always last
The `/{short_code}` wildcard route matches any single-segment path. If registered first, it would intercept `/health`, `/docs`, `/api/auth/login`, and every other route. The URL router is always registered last in `main.py` so all specific routes are matched before the wildcard.

---

## Performance

| Operation | Without Cache | With Cache |
|-----------|--------------|-----------|
| First redirect (cold) | 10–20ms | 10–20ms + cache write |
| Repeat redirect (warm) | 10–20ms | **<1ms** |
| Invalid code (first hit) | 10–20ms | 10–20ms + negative cache |
| Invalid code (repeat) | 10–20ms | **<1ms** |
| URL creation | 15–30ms | 15–30ms + cache warm |

Redis connection pool: 20 max connections
PostgreSQL connection pool: 10 base, 20 overflow

---

## Security

| Concern | Implementation |
|---------|---------------|
| Password storage | bcrypt with auto-generated salt (cost factor 12) |
| Authentication | JWT HS256, 24-hour expiry |
| Authorization | Ownership checks on all mutations |
| Secrets | `.env` file, excluded from git |
| SQL injection | SQLAlchemy parameterized queries — no raw SQL |
| Input validation | Pydantic v2 validates all request bodies |
| Custom aliases | Alphanumeric only, 3–50 chars, lowercase enforced |
| Password length | 8–72 character limits (bcrypt max) |

---

## Background Jobs

| Job | Schedule | What it does |
|-----|---------|-------------|
| `cleanup_expired_urls` | Every hour | Finds links past `expires_at`, sets `is_active=False`, removes from Redis |
| `cleanup_old_clicks` | Every Sunday 2am | Deletes `clicks` rows older than 90 days to prevent table bloat |

Jobs are registered with APScheduler's `AsyncIOScheduler` which runs on the same event loop as FastAPI — no threads, no blocking. Both jobs open their own DB sessions independently of the request lifecycle.

---

## AI Features

All AI endpoints use OpenAI GPT-3.5-turbo. They require a valid `OPENAI_API_KEY` in `.env` and a valid JWT token in the request.

| Endpoint | Model | Temp | Max Tokens | Use case |
|----------|-------|------|-----------|---------|
| `/ai/suggest-alias` | gpt-3.5-turbo | 0.7 | 150 | Creative suggestions |
| `/ai/detect-malicious` | gpt-3.5-turbo | 0.2 | 300 | Consistent analysis |
| `/ai/utm-tags` | gpt-3.5-turbo | 0.4 | 300 | Structured output |

Lower temperature for security-sensitive endpoints (malicious detection) ensures consistent, reliable responses rather than creative variation.

---

## Dependencies

```
fastapi==0.115.0              # Web framework
uvicorn==0.30.6               # ASGI server
sqlalchemy[asyncio]==2.0.35   # Async ORM
asyncpg==0.30.0               # Async PostgreSQL driver
alembic==1.13.3               # Database migrations
pydantic==2.9.2               # Data validation
pydantic[email]==2.9.2        # Email validation
pydantic-settings==2.5.2      # Settings management
python-dotenv==1.0.1          # .env file loading
redis[hiredis]==5.0.8         # Async Redis client + C parser
bcrypt==4.2.0                 # Password hashing
python-jose[cryptography]==3.3.0  # JWT tokens
python-multipart==0.0.12      # Form data parsing
apscheduler==3.10.4           # Background job scheduling
user-agents==2.2.0            # User-Agent string parsing
httpx==0.27.2                 # Async HTTP client
openai==1.30.1                # OpenAI API client
```

---

## Roadmap

- [x] Phase 1 — Core URL Shortener (Base62, redirect, custom aliases)
- [x] Phase 2 — Redis Caching Layer (cache-first, negative caching, invalidation)
- [x] Phase 3 — JWT Authentication (register, login, ownership)
- [x] Phase 4 — Analytics Engine (click tracking, device/browser/referrer)
- [x] Phase 5 — Expiry + Background Jobs (APScheduler, cleanup jobs)
- [x] Phase 6 — AI Integration (alias suggestions, malicious detection, UTM tags)
- [ ] Phase 7 — Docker + Deployment (docker-compose, Railway/Render)
- [ ] QR code generation for every short link
- [ ] Geo-based redirects (different destination per country)
- [ ] Bulk URL shortening API
- [ ] Link password protection
- [ ] Rate limiting per user (Redis-based token bucket)
- [ ] Browser extension
- [ ] Custom domains (`yourdomain.com/code`)
- [ ] Webhook notifications on click thresholds

---

## Contributing

1. Fork the repository
2. Create a feature branch

```bash
git checkout -b feat/your-feature-name
```

3. Commit your changes using conventional commits

```bash
git commit -m "feat: add geo-based redirects"
git commit -m "fix: handle expired token edge case"
git commit -m "chore: update dependencies"
```

4. Push to your branch

```bash
git push origin feat/your-feature-name
```

5. Open a Pull Request

---


---

## Author

Aaryam Singh

---

*Built as a backend engineering portfolio project demonstrating production patterns: async architecture, caching strategy, authentication, analytics pipelines, background jobs, and AI integration.*
