from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import bugs
from app.core.config import settings

app = FastAPI(
    title="Quality Platform API",
    description="Bug status dashboard API",
    version="1.0.0",
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(bugs.router, prefix="/api", tags=["bugs"])

@app.get("/api/auth/config")
def get_auth_config():
    """
    Return AAD config for frontend MSAL.js.
    This endpoint is public (no auth required).
    """
    return {
        "clientId": settings.AAD_CLIENT_ID,
        "authority": f"https://login.microsoftonline.com/{settings.AAD_TENANT_ID}",
        "redirectUri": "/",
    }

# Static files (frontend)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
