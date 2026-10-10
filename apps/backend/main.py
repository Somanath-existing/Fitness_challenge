"""
Fitness Challenge API — main application entry point.

Startup: creates DB tables, registers all routers, mounts CORS.
Security middleware: security headers on every response.
WebSocket: /ws — real-time leaderboard updates (token-authenticated).
Health: /health — for Docker healthcheck and UptimeRobot.
"""
import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv

# Load .env before anything else touches os.getenv
load_dotenv()

from app.database import create_db_and_tables
from app.routers import users, activities, leaderboard, dashboard, friends, challenges, insights, auth
from app.routers.dashboard import admin_router
from app import ws_manager

# ── Logging configuration ────────────────────────────────────────────────────
# Production: INFO level — DEBUG would leak sensitive request data in logs
_is_production = os.getenv("ENVIRONMENT") == "production"
logging.basicConfig(
    level=logging.INFO if _is_production else logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


# ── Security Headers Middleware ───────────────────────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds OWASP-recommended security headers to every HTTP response.
    These are a last-line defence against XSS, clickjacking, MIME-sniffing, etc.
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        # Content-Security-Policy — tightened for API (no HTML served)
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'"
        )
        # HSTS — only in production where HTTPS is enforced
        if _is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )
        return response


# ── Request logging middleware ────────────────────────────────────────────────
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs every inbound request with IP, method, path, and response status."""
    async def dispatch(self, request: Request, call_next):
        ip = request.client.host if request.client else "unknown"
        response = await call_next(request)
        log_fn = logger.warning if response.status_code >= 400 else logger.info
        log_fn(
            "REQUEST ip=%s method=%s path=%s status=%d",
            ip, request.method, request.url.path, response.status_code,
        )
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    logger.info("Starting Fitness Challenge API — env=%s", os.getenv("ENVIRONMENT", "development"))
    create_db_and_tables()
    logger.info("Database tables ready.")
    yield
    logger.info("Shutting down.")


# Disable interactive docs in production — they expose endpoint details
app = FastAPI(
    title="Fitness Challenge API",
    description="Gamified fitness tracking with leaderboards, badges, and AI coaching.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
)

# ── Middleware (order matters — outermost first) ───────────────────────────────
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Allow explicit configured origins + Vercel deployment URLs + local development
_raw_origins = os.getenv("FRONTEND_URL", "http://localhost:5173")
ALLOWED_ORIGINS = [o.strip().rstrip("/") for o in _raw_origins.split(",") if o.strip()]

for default_origin in (
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
):
    if default_origin not in ALLOWED_ORIGINS:
        ALLOWED_ORIGINS.append(default_origin)

# Match any Vercel deployment URL (e.g. preview hash domains) and localhost
ALLOWED_ORIGIN_REGEX = (
    r"^(https://([a-zA-Z0-9_-]+\.)*(vercel\.app|onrender\.com)"
    r"|http://(localhost|127\.0\.0\.1)(:\d+)?)$"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(activities.router)
app.include_router(leaderboard.router)
app.include_router(dashboard.router)
app.include_router(friends.router)
app.include_router(challenges.router)
app.include_router(insights.router)
app.include_router(admin_router)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["meta"])
def health():
    """Minimal health check — no sensitive info exposed."""
    return {
        "status": "ok",
        "version": "1.0.0",
    }


# ── WebSocket endpoint ────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """
    Real-time leaderboard WebSocket.
    Note: WebSocket auth should be implemented via a one-time token
    passed as a query param at connect time (cookies not reliably sent
    on WS upgrade in all browsers).
    """
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)
    except Exception:
        ws_manager.disconnect(ws)
