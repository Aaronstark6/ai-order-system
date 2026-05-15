from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routes import (
    core_router,
    images_router,
    parse_router,
    templates_router,
)


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
UPLOADS_DIR = BASE_DIR / "uploads"


# ====================
# FastAPI App
# ====================

app = FastAPI(title="AI Order System V2")


# ====================
# Middleware
# ====================


# ====================
# Static Files
# ====================

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")


# ====================
# Routers
# ====================

app.include_router(images_router)
app.include_router(parse_router)
app.include_router(templates_router)
app.include_router(core_router)


# ====================
# Static Entrypoints
# ====================

@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/config")
def config_page():
    return FileResponse(STATIC_DIR / "config.html")


# ====================
# Health Check
# ====================

@app.get("/api/health")
def api_health():
    return {
        "success": True,
        "app": "ai-order-system",
        "version": "v3",
    }
