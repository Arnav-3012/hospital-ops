"""
main.py — FastAPI application entry point.

Run with (from project root):
  venv/bin/uvicorn backend.app.main:app --reload --port 8000
"""

import sys
from pathlib import Path

# Ensure 'backend/' is on sys.path so 'from app.xxx' imports resolve
# correctly whether uvicorn is invoked as backend.app.main or app.main.
_backend_dir = str(Path(__file__).resolve().parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.security import HTTPBearer

from app.routers import (
    admissions,
    appointments,
    beds,
    billing,
    departments,
    doctors,
    inventory,
    patients,
    prescriptions,
)
from app.routers import analytics, audit, auth, nl_query


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown hook
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Hospital Operations API started successfully")
    yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Hospital Operations Intelligence System",
    version="1.0.0",
    description="NMIMS  DS Project - Semester IV",
    lifespan=lifespan,
)

security = HTTPBearer()

# ---------------------------------------------------------------------------
# CORS — allow all origins so the Streamlit frontend can reach the API
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(doctors.router)
app.include_router(departments.router)
app.include_router(beds.router)
app.include_router(appointments.router)
app.include_router(admissions.router)
app.include_router(prescriptions.router)
app.include_router(billing.router)
app.include_router(inventory.router)
app.include_router(analytics.router, prefix="/analytics",  tags=["analytics"])
app.include_router(nl_query.router,  prefix="/query",      tags=["NL-to-SQL"])
app.include_router(audit.router,     prefix="/audit-log",  tags=["audit"])


# ---------------------------------------------------------------------------
# Custom OpenAPI schema — adds bearerAuth to Swagger Authorize popup
# ---------------------------------------------------------------------------
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Hospital Operations Intelligence System",
        version="1.0.0",
        description="NMIMS MBATech DS Project - Semester IV",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    for path in openapi_schema["paths"].values():
        for operation in path.values():
            operation["security"] = [{"bearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi


# ---------------------------------------------------------------------------
# Auth — me endpoint
# ---------------------------------------------------------------------------
@app.get("/auth/me", tags=["auth"])
def me(current_user: dict = Depends(auth.get_current_user)):
    return current_user


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    return {
        "message": "Hospital Operations API is running",
        "docs":    "/docs",
    }
