from app.logger import get_logger
from app.v4_renderer_core import render_order_object
from app.v4_validator import validate_order_object


logger = get_logger(__name__)


def run_core_pipeline(order_object):
    logger.info("[CorePipeline] Pipeline started")
    validation_result = validate_order_object(order_object)
    logger.info(
        "[CorePipeline] Validation finished: valid=%s errors=%s warnings=%s",
        validation_result.get("valid"),
        len(validation_result.get("errors", [])),
        len(validation_result.get("warnings", [])),
    )

    if not validation_result.get("valid"):
        logger.info("[CorePipeline] Validation failed, renderer skipped")
        return {
            "success": False,
            "stage": "validation_failed",
            "validation": validation_result,
            "render": None,
        }

    render_result = render_order_object(order_object)
    logger.info(
        "[CorePipeline] Render finished: success=%s warnings=%s",
        render_result.get("success"),
        len(render_result.get("warnings", [])),
    )
    return {
        "success": True,
        "stage": "rendered",
        "validation": validation_result,
        "render": render_result,
    }
