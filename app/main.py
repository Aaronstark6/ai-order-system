from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.logger import get_logger
from app.routes import (
    core_router,
    images_router,
    parse_router,
    templates_router,
    v4_router,
)
from app.runtime_paths import get_base_dir


BASE_DIR = get_base_dir()
STATIC_DIR = BASE_DIR / "static"
UPLOADS_DIR = BASE_DIR / "uploads"
logger = get_logger(__name__)


# ====================
# FastAPI App
# ====================

app = FastAPI(title="AI Order System V4-dev")
logger.info("FastAPI app initialized")


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
app.include_router(v4_router)
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


@app.get("/v4-schema")
def v4_schema_page():
    return FileResponse(STATIC_DIR / "v4_schema.html")


@app.get("/v4-workbench")
def v4_workbench_page():
    return FileResponse(STATIC_DIR / "v4_workbench.html")


@app.get("/v4-product-types")
def v4_product_types_page():
    return FileResponse(STATIC_DIR / "v4_product_types.html")


@app.get("/v4-order-object")
def v4_order_object_page():
    return FileResponse(STATIC_DIR / "v4_order_object.html")


@app.get("/v4-validator")
def v4_validator_page():
    return FileResponse(STATIC_DIR / "v4_validator.html")


@app.get("/v4-renderer-core")
def v4_renderer_core_page():
    return FileResponse(STATIC_DIR / "v4_renderer_core.html")


@app.get("/v4-core-pipeline")
def v4_core_pipeline_page():
    return FileResponse(STATIC_DIR / "v4_core_pipeline.html")


@app.get("/v4-structured-mapping")
def v4_structured_mapping_page():
    return FileResponse(STATIC_DIR / "v4_structured_mapping.html")


@app.get("/v4-block-merge-rules")
def v4_block_merge_rules_page():
    return FileResponse(STATIC_DIR / "v4_block_merge_rules.html")


@app.get("/v4-table-mapping")
def v4_table_mapping_page():
    return FileResponse(STATIC_DIR / "v4_table_mapping.html")


# ====================
# Health Check
# ====================

@app.get("/api/health")
def api_health():
    return {
        "success": True,
        "app": "ai-order-system",
        "version": "v4-dev",
        "branch": "v4-dev",
        "stage": "V4 experimental integration",
    }
