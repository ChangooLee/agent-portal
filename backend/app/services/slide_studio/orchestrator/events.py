"""SSE Event Schema and Emit Functions"""
from typing import Dict, Any, Optional
from app.services.slide_studio.ir.schema import SlideStage


def format_sse_event(event_type: str, data: Dict[str, Any]) -> str:
    """Format SSE event"""
    import json
    event_str = f"event: {event_type}\n"
    data_str = json.dumps(data, ensure_ascii=False)
    event_str += f"data: {data_str}\n\n"
    return event_str


def emit_deck_created(deck_id: str) -> str:
    """Emit deck.created event"""
    return format_sse_event("deck.created", {"deck_id": deck_id})


def emit_deck_plan_created(deck_id: str, slides: list) -> str:
    """Emit deck.plan.created event"""
    return format_sse_event("deck.plan.created", {
        "deck_id": deck_id,
        "slides": slides
    })


def emit_slide_stage(
    deck_id: str,
    slide_id: str,
    stage: SlideStage,
    progress: float = 0.0,
    message: str = ""
) -> str:
    """Emit slide.stage event"""
    return format_sse_event("slide.stage", {
        "deck_id": deck_id,
        "slide_id": slide_id,
        "stage": stage.value,
        "progress": progress,
        "message": message
    })


def emit_slide_preview_updated(
    deck_id: str,
    slide_id: str,
    thumbnail_url: Optional[str] = None,
    thumbnail_data_uri: Optional[str] = None
) -> str:
    """Emit slide.preview.updated event"""
    data = {
        "deck_id": deck_id,
        "slide_id": slide_id
    }
    if thumbnail_url:
        data["thumbnail_url"] = thumbnail_url
    if thumbnail_data_uri:
        data["thumbnail_data_uri"] = thumbnail_data_uri
    return format_sse_event("slide.preview.updated", data)


def emit_slide_issues(
    deck_id: str,
    slide_id: str,
    issues: list,
    score: Optional[float] = None,
    metrics: Optional[Dict[str, Any]] = None
) -> str:
    """Emit slide.issues event"""
    data = {
        "deck_id": deck_id,
        "slide_id": slide_id,
        "issues": issues
    }
    if score is not None:
        data["score"] = score
    if metrics:
        data["metrics"] = metrics
    return format_sse_event("slide.issues", data)


def emit_slide_finalized(
    deck_id: str,
    slide_id: str,
    score: Optional[float] = None,
    editability_estimate: Optional[float] = None
) -> str:
    """Emit slide.finalized event"""
    data = {
        "deck_id": deck_id,
        "slide_id": slide_id
    }
    if score is not None:
        data["score"] = score
    if editability_estimate is not None:
        data["editability_estimate"] = editability_estimate
    return format_sse_event("slide.finalized", data)


def emit_export_started(deck_id: str, formats: list) -> str:
    """Emit export.started event"""
    return format_sse_event("export.started", {
        "deck_id": deck_id,
        "formats": formats
    })


def emit_export_finished(
    deck_id: str,
    pptx_path: Optional[str] = None,
    pdf_path: Optional[str] = None,
    stats: Optional[Dict[str, Any]] = None
) -> str:
    """Emit export.finished event"""
    data = {"deck_id": deck_id}
    if pptx_path:
        data["pptx_path"] = pptx_path
    if pdf_path:
        data["pdf_path"] = pdf_path
    if stats:
        data["stats"] = stats
    return format_sse_event("export.finished", data)


def emit_job_error(scope: str, id: str, error: str) -> str:
    """Emit job.error event"""
    return format_sse_event("job.error", {
        "scope": scope,  # "deck" or "slide"
        "id": id,
        "error": error
    })


def emit_job_stopped(deck_id: str) -> str:
    """Emit job.stopped event"""
    return format_sse_event("job.stopped", {"deck_id": deck_id})
