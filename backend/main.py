import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from supabase import create_client, Client

from routers import auth_router, scan_router, reports_router, users_router, products_router

load_dotenv()

# ---------------------------------------------------------------------------
# Supabase client (application-wide singleton)
# ---------------------------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

supabase_client: Client | None = None
if SUPABASE_URL and SUPABASE_SERVICE_KEY:
    supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def get_supabase() -> Client:
    """Dependency: returns the Supabase service-role client."""
    if supabase_client is None:
        raise RuntimeError(
            "Supabase client is not initialised. "
            "Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables."
        )
    return supabase_client


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Legal Metrology Compliance System API",
    description=(
        "Backend API for scanning packaged-commodity labels, checking them "
        "against Legal Metrology (Packaged Commodities) Rules 2011, and "
        "generating compliance reports."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

origins = [
    FRONTEND_URL,
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    # Allow all *.vercel.app subdomains
    "https://*.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth_router.router)
app.include_router(scan_router.router)
app.include_router(reports_router.router)
app.include_router(users_router.router)
app.include_router(products_router.router)

# ---------------------------------------------------------------------------
# Root & health endpoints
# ---------------------------------------------------------------------------


@app.get("/", tags=["Meta"])
def root():
    """API root — returns service identification and available docs URLs."""
    return {
        "service": "Legal Metrology Compliance System API",
        "version": "1.0.0",
        "description": (
            "Scan packaged-commodity labels and check compliance with "
            "LM (PC) Rules, 2011."
        ),
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
    }


@app.get("/health", tags=["Meta"])
def health_check():
    """Health-check endpoint used by Render and load-balancers."""
    db_ok = False
    try:
        from db.connection import get_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        db_ok = True
    except Exception:
        db_ok = False

    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "unavailable",
        "supabase": "configured" if supabase_client is not None else "not configured",
    }
