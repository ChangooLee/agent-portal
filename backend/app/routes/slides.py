"""
Slide Studio API Router

POST /api/slides/generate - Generate deck
GET /api/slides/{deck_id}/events - SSE stream
GET /api/slides/{deck_id} - Get deck state
POST /api/slides/{deck_id}/stop - Stop generation
"""
import logging
import uuid
import asyncio
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.slide_studio.ir.planner import deck_planner
from app.services.slide_studio.orchestrator.state import DeckState, SlideState
from app.services.slide_studio.orchestrator.runner import Orchestrator
from app.services.slide_studio.orchestrator.events import (
    emit_deck_created,
    emit_deck_plan_created,
    emit_job_stopped
)
from app.services.slide_studio.store.repo import slide_studio_repo
from app.services.slide_studio.theme.selector import theme_selector
from app.services.slide_studio.ir.schema import DeckIR
from app.services.agent_registry_service import agent_registry, AgentType
from app.services.agent_trace_adapter import agent_trace_adapter
from app.services.slide_studio.orchestrator.metrics import start_slide_span, inject_context_to_carrier

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/slides", tags=["slides"])
api_router = APIRouter(prefix="/api/slides", tags=["slides"])


# Request/Response Models
class GenerateRequest(BaseModel):
    """Generate deck request"""
    prompt: str = Field(..., description="Topic/prompt for deck")
    goal: Optional[str] = Field(None, description="Goal/objective")
    audience: Optional[str] = Field(None, description="Target audience")
    tone: Optional[str] = Field(None, description="Tone (formal, casual, etc.)")
    slide_count: int = Field(10, description="Number of slides", ge=1, le=50)
    options: Optional[Dict[str, Any]] = Field(None, description="Additional options")


class GenerateResponse(BaseModel):
    """Generate deck response"""
    deck_id: str
    events_url: str


class DeckStatusResponse(BaseModel):
    """Deck status response"""
    deck_id: str
    title: str
    status: str
    slides_status: Dict[str, Dict[str, Any]]
    ir_summary: Optional[Dict[str, Any]] = None


# Background task storage (for stopping)
_active_orchestrators: Dict[str, Orchestrator] = {}


async def _generate_deck_background(deck_id: str, deck_state: DeckState):
    """Background task for deck generation"""
    # Get parent trace_id and root_carrier from deck_state
    parent_trace_id = deck_state.trace_id
    root_carrier = deck_state.root_carrier or {}
    
    # Get agent info from deck_state (stored during trace start)
    agent_id = "slide-studio"
    agent_name = "Slide Studio Agent"
    agent_type = AgentType.SLIDES.value
    
    # Use start_slide_span for the root of the deck generation process
    # Use root_carrier to ensure all child spans share the same trace_id
    with start_slide_span(
        name="gen_ai.session",  # GenAI standard for root agent session
        attributes={
            "slide.deck_id": deck_id,
            "slide.deck.title": deck_state.title,
            "slide.deck.slide_count": len(deck_state.slides),
            "slide.deck.theme_id": deck_state.theme_id or "",
            "agent.id": agent_id,
            "agent.name": agent_name,
            "agent.type": agent_type,
            "gen_ai.agent.id": agent_id,
            "gen_ai.agent.name": agent_name,
            "service.name": f"agent-{agent_type}"  # 모니터링 화면에서 사용
        },
        parent_carrier=root_carrier,  # Use root_carrier from generate_deck to maintain trace context
        parent_trace_id=parent_trace_id
    ) as root_span:
        try:
            orchestrator = Orchestrator(deck_state)
            _active_orchestrators[deck_id] = orchestrator
            
            # Run orchestrator and collect events
            # Events will be sent via SSE stream
            async for event in orchestrator.run_all_slides(parent_trace_id=parent_trace_id):
                # Events are handled by SSE stream endpoint
                pass
            
            # Mark deck as ready
            deck_state.status = "ready"
            slide_studio_repo.save_deck_state(deck_state)
            
            # Calculate final metrics for the deck
            final_deck_ir = slide_studio_repo.get_deck_ir(deck_id)
            total_score = 0.0
            total_reflections = 0
            total_issues = 0
            completed_slides = 0
            
            if final_deck_ir:
                for slide_ir in final_deck_ir.slides:
                    if slide_ir.score is not None:
                        total_score += slide_ir.score
                        completed_slides += 1
                    total_issues += len(slide_ir.issues)
            
            # Get reflection count from deck_state (SlideState)
            for slide_state in deck_state.slides.values():
                total_reflections += slide_state.reflection_count
            
            avg_score = total_score / completed_slides if completed_slides > 0 else 0.0
            
            # End the trace with final outputs
            if parent_trace_id:
                await agent_trace_adapter.end_trace(
                    trace_id=parent_trace_id,
                    outputs={
                        "deck_id": deck_id,
                        "total_slides": len(deck_state.slides),
                        "avg_score": round(avg_score, 2),
                        "total_reflections": total_reflections,
                        "total_issues": total_issues,
                        "success": True
                    },
                    cost=0.0,  # TODO: Calculate actual cost
                    tokens=0  # TODO: Calculate actual tokens
                )
            
            logger.info(f"[{deck_id}] Deck generation completed. Avg Score: {avg_score:.2f}")
            
        except Exception as e:
            logger.error(f"Deck generation error for {deck_id}: {e}", exc_info=True)
            if parent_trace_id:
                await agent_trace_adapter.end_trace(
                    trace_id=parent_trace_id,
                    outputs={"success": False},
                    error=str(e)
                )
            deck_state.status = "error"
            slide_studio_repo.save_deck_state(deck_state)
        finally:
            if deck_id in _active_orchestrators:
                del _active_orchestrators[deck_id]


@router.post("/generate", response_model=GenerateResponse)
@api_router.post("/generate", response_model=GenerateResponse)
async def generate_deck(
    request: GenerateRequest,
    background_tasks: BackgroundTasks
):
    """
    Generate a new deck.
    
    Returns deck_id and events_url for SSE streaming.
    """
    try:
        deck_id = str(uuid.uuid4())
        
        logger.info(f"[{deck_id}] generate_deck: Starting generation - prompt: {request.prompt[:50]}..., slide_count: {request.slide_count}, goal: {request.goal}, audience: {request.audience}, tone: {request.tone}")
        
        # 1. Register agent and start trace
        agent_info = await agent_registry.register_or_get(
            name="slide-studio",
            agent_type=AgentType.SLIDES,
            project_id="default-project",  # TODO: Make dynamic
            description="AI Slide Generation Studio"
        )
        
        # Create root OTEL span for the entire deck generation
        # This ensures all child spans share the same trace_id
        root_carrier = {}
        trace_id = None
        
        with start_slide_span(
            name="gen_ai.session",  # GenAI standard for root agent session
            attributes={
                "slide.deck_id": deck_id,
                "slide.deck.title": request.prompt[:50],
                "agent.id": "slide-studio",
                "agent.name": "Slide Studio Agent",
                "agent.type": AgentType.SLIDES.value,
                "gen_ai.agent.id": "slide-studio",
                "gen_ai.agent.name": "Slide Studio Agent",
                "service.name": "agent-slides"
            },
            parent_carrier=None  # Root span, no parent
        ) as root_span:
            # Extract trace_id from the root span
            try:
                from opentelemetry import trace
                span_context = trace.get_current_span().get_span_context()
                if span_context and hasattr(span_context, 'trace_id'):
                    trace_id = format(span_context.trace_id, '032x')
            except Exception as e:
                logger.warning(f"Failed to extract trace_id from span: {e}")
            
            # If trace_id extraction failed, generate one and register with agent_trace_adapter
            if not trace_id:
                trace_id = await agent_trace_adapter.start_trace(
                    agent_id=agent_info.get("id", "slide-studio"),
                    agent_name="Slide Studio Agent",
                    agent_type=AgentType.SLIDES.value,
                    project_id="default-project",  # TODO: Make dynamic
                    inputs={
                        "prompt": request.prompt,
                        "slide_count": request.slide_count,
                        "goal": request.goal,
                        "audience": request.audience,
                        "tone": request.tone
                    }
                )
            
            # Extract the root span's context as carrier for child spans
            inject_context_to_carrier(root_carrier)
        
        logger.info(f"[{deck_id}] Agent registered and trace started: {trace_id}, root_carrier: {root_carrier}")
        
        # Select theme first
        logger.info(f"[{deck_id}] generate_deck: Selecting theme...")
        with start_slide_span(
            name="gen_ai.agent.theme_selection",
            attributes={"slide.deck_id": deck_id},
            parent_trace_id=trace_id
        ) as span:
            theme = await theme_selector.select_theme(
                prompt=request.prompt,
                goal=request.goal,
                audience=request.audience,
                tone=request.tone,
                trace_id=trace_id
            )
            if hasattr(span, 'set_attribute'):
                span.set_attribute("slide.deck.theme_id", theme.theme_id if theme else "default")
        logger.info(f"[{deck_id}] generate_deck: Theme selected - theme_id: {theme.theme_id if theme else 'None'}")
        
        # Plan deck
        logger.info(f"[{deck_id}] generate_deck: Planning deck structure...")
        with start_slide_span(
            name="gen_ai.agent.deck_planning",
            attributes={"slide.deck_id": deck_id},
            parent_trace_id=trace_id
        ) as span:
            planner = deck_planner
            slide_plans = await planner.plan_deck(
                prompt=request.prompt,
                slide_count=request.slide_count,
                goal=request.goal,
                audience=request.audience,
                tone=request.tone,
                trace_id=trace_id,
                **request.options or {}
            )
            if hasattr(span, 'set_attribute'):
                span.set_attribute("slide.deck.planned_slide_count", len(slide_plans))
        logger.info(f"[{deck_id}] generate_deck: Deck plan created - {len(slide_plans)} slides")
        
        # Create theme variant map
        theme_variant_map = {}
        tone_tags = [request.tone] if request.tone else ["professional"]
        for slide_plan in slide_plans:
            variant_id = theme_selector.select_variant_for_slide_type(
                theme=theme,
                slide_type=slide_plan.slide_type.value,
                tone_tags=tone_tags
            )
            theme_variant_map[slide_plan.slide_type.value] = variant_id
        
        # Create deck state with theme, trace_id, and root_carrier
        deck_state = DeckState(
            deck_id=deck_id,
            title=request.prompt[:50],
            theme_id=theme.theme_id if theme else None,
            theme_variant_map=theme_variant_map,
            trace_id=trace_id,
            goal=request.goal,
            audience=request.audience,
            tone=request.tone,
            root_carrier=root_carrier  # Store root carrier for context propagation
        )
        
        # Create DeckIR with theme
        deck_ir = DeckIR(
            deck_id=deck_id,
            title=request.prompt[:50],
            theme_id=theme.theme_id,
            theme_variant_map=theme_variant_map
        )
        slide_studio_repo.save_deck_ir(deck_ir)
        
        # Create slide states
        for slide_plan in slide_plans:
            slide_state = SlideState(
                slide_id=slide_plan.slide_id,
                slide_plan=slide_plan
            )
            deck_state.add_slide(slide_plan.slide_id, slide_state)
        
        # Save deck state
        slide_studio_repo.save_deck_state(deck_state)
        
        # Start background generation
        background_tasks.add_task(_generate_deck_background, deck_id, deck_state)
        
        return GenerateResponse(
            deck_id=deck_id,
            events_url=f"/api/slides/{deck_id}/events"
        )
        
    except Exception as e:
        logger.error(f"Generate deck error: {e}")
        # End trace with error if it was started
        if 'trace_id' in locals() and trace_id:
            await agent_trace_adapter.end_trace(
                trace_id=trace_id,
                outputs={"success": False},
                error=str(e)
            )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{deck_id}/events")
@api_router.get("/{deck_id}/events")
async def get_deck_events(deck_id: str):
    """
    SSE stream for deck events.
    
    Returns Server-Sent Events stream with real-time updates.
    """
    deck_state = slide_studio_repo.get_deck_state(deck_id)
    if not deck_state:
        raise HTTPException(status_code=404, detail="Deck not found")
    
    async def event_generator():
        """Generate SSE events"""
        try:
            # Emit deck.created
            yield emit_deck_created(deck_id)
            
            # Emit deck.plan.created
            slides_data = [
                {
                    "slide_id": slide_state.slide_id,
                    "title": slide_state.slide_plan.title,
                    "type": slide_state.slide_plan.slide_type.value,
                    "goal": slide_state.slide_plan.goal
                }
                for slide_state in deck_state.slides.values()
            ]
            yield emit_deck_plan_created(deck_id, slides_data)
            
            # Create orchestrator and stream events
            orchestrator = Orchestrator(deck_state)
            _active_orchestrators[deck_id] = orchestrator
            
            # Get parent trace_id from deck_state
            parent_trace_id = deck_state.trace_id if hasattr(deck_state, 'trace_id') else None
            
            async for event in orchestrator.run_all_slides(parent_trace_id=parent_trace_id):
                yield event
            
            # Cleanup
            if deck_id in _active_orchestrators:
                del _active_orchestrators[deck_id]
                
        except Exception as e:
            logger.error(f"SSE stream error for {deck_id}: {e}")
            yield f"event: error\ndata: {str(e)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/{deck_id}", response_model=DeckStatusResponse)
@api_router.get("/{deck_id}", response_model=DeckStatusResponse)
async def get_deck_status(deck_id: str):
    """Get deck status"""
    deck_state = slide_studio_repo.get_deck_state(deck_id)
    if not deck_state:
        raise HTTPException(status_code=404, detail="Deck not found")
    
    slides_status = {}
    for slide_id, slide_state in deck_state.slides.items():
        slides_status[slide_id] = {
            "stage": slide_state.stage.value,
            "progress": slide_state.progress,
            "message": slide_state.message,
            "score": slide_state.score,
            "issues_count": len(slide_state.issues)
        }
    
    ir_summary = None
    if deck_state.ir:
        ir_summary = {
            "slide_count": len(deck_state.ir.slides),
            "title": deck_state.ir.title
        }
    
    return DeckStatusResponse(
        deck_id=deck_state.deck_id,
        title=deck_state.title,
        status=deck_state.status,
        slides_status=slides_status,
        ir_summary=ir_summary
    )


@router.post("/{deck_id}/stop")
@api_router.post("/{deck_id}/stop")
async def stop_deck_generation(deck_id: str):
    """Stop deck generation"""
    deck_state = slide_studio_repo.get_deck_state(deck_id)
    if not deck_state:
        raise HTTPException(status_code=404, detail="Deck not found")
    
    # Mark as stopped
    deck_state.stopped = True
    deck_state.status = "stopped"
    
    # Stop orchestrator if active
    if deck_id in _active_orchestrators:
        del _active_orchestrators[deck_id]
    
    slide_studio_repo.save_deck_state(deck_state)
    
    return {"status": "stopped", "deck_id": deck_id}


class FixLayoutRequest(BaseModel):
    """Fix layout request"""
    mode: str = Field("auto", description="Fix mode: auto, split, simplify")
    scope: str = Field("deck", description="Scope: deck, slide")
    slide_id: Optional[str] = Field(None, description="Slide ID (if scope is slide)")


@router.get("/{deck_id}/quality")
@api_router.get("/{deck_id}/quality")
async def get_deck_quality(deck_id: str):
    """Get deck quality metrics"""
    deck_state = slide_studio_repo.get_deck_state(deck_id)
    if not deck_state:
        raise HTTPException(status_code=404, detail="Deck not found")
    
    from app.services.slide_studio.verify.metrics import quality_metrics_calculator
    
    slides_quality = {}
    for slide_id, slide_state in deck_state.slides.items():
        if slide_state.ir:
            metrics = quality_metrics_calculator.calculate_metrics(slide_state.ir)
            score = quality_metrics_calculator.calculate_score(metrics)
            slides_quality[slide_id] = {
                "score": score,
                "metrics": metrics.model_dump(),
                "issues_count": len(slide_state.ir.issues),
                "error_issues_count": sum(
                    1 for issue in slide_state.ir.issues
                    if issue.get("severity") == "error"
                )
            }
    
    return {
        "deck_id": deck_id,
        "slides_quality": slides_quality
    }


@router.post("/{deck_id}/fix-layout")
@api_router.post("/{deck_id}/fix-layout")
async def fix_layout(deck_id: str, request: FixLayoutRequest):
    """Fix layout issues"""
    deck_state = slide_studio_repo.get_deck_state(deck_id)
    if not deck_state:
        raise HTTPException(status_code=404, detail="Deck not found")
    
    from app.services.slide_studio.fix.auto_fix import auto_fix
    from app.services.slide_studio.layout.engine import layout_engine
    
    fixed_count = 0
    
    if request.scope == "slide" and request.slide_id:
        slide_state = deck_state.get_slide(request.slide_id)
        if slide_state and slide_state.ir:
            # Apply fix
            fixed_ir = auto_fix.apply_fix(slide_state.ir, request.mode)
            fixed_ir = layout_engine.layout_slide(fixed_ir)
            slide_state.ir = fixed_ir
            fixed_count = 1
    elif request.scope == "deck":
        # Fix all slides
        for slide_state in deck_state.slides.values():
            if slide_state.ir:
                fixed_ir = auto_fix.apply_fix(slide_state.ir, request.mode)
                fixed_ir = layout_engine.layout_slide(fixed_ir)
                slide_state.ir = fixed_ir
                fixed_count += 1
    
    slide_studio_repo.save_deck_state(deck_state)
    
    return {
        "status": "fixed",
        "deck_id": deck_id,
        "fixed_slides": fixed_count
    }


class ExportRequest(BaseModel):
    """Export request"""
    formats: List[str] = Field(["pptx"], description="Export formats: pptx, pdf")


@router.post("/{deck_id}/export")
@api_router.post("/{deck_id}/export")
async def export_deck(deck_id: str, request: ExportRequest):
    """Export deck to PPTX/PDF"""
    from fastapi.responses import FileResponse
    deck_state = slide_studio_repo.get_deck_state(deck_id)
    if not deck_state:
        raise HTTPException(status_code=404, detail="Deck not found")
    
    # Get deck IR
    deck_ir = slide_studio_repo.get_deck_ir(deck_id)
    if not deck_ir:
        # Build deck IR from states
        from app.services.slide_studio.ir.schema import DeckIR
        slides_ir = [
            slide_state.ir
            for slide_state in deck_state.slides.values()
            if slide_state.ir
        ]
        deck_ir = DeckIR(
            deck_id=deck_id,
            title=deck_state.title,
            slides=slides_ir
        )
        slide_studio_repo.save_deck_ir(deck_ir)
    
    from app.services.slide_studio.export.pptx_exporter import pptx_exporter
    from app.services.slide_studio.export.pdf_exporter import pdf_exporter
    from app.services.slide_studio.store.artifact import artifact_storage
    import tempfile
    
    results = {}
    
    # Export PPTX
    if "pptx" in request.formats:
        try:
            with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
                pptx_path = tmp.name
            
            pptx_exporter.export_deck(deck_ir, pptx_path)
            download_path = artifact_storage.save_pptx(deck_id, pptx_path)
            results["pptx"] = download_path
        except Exception as e:
            logger.error(f"PPTX export error: {e}")
            results["pptx"] = None
    
    # Export PDF
    if "pdf" in request.formats:
        pptx_file = artifact_storage.get_pptx_path(deck_id)
        if pptx_file:
            try:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    pdf_path = tmp.name
                
                pdf_result = pdf_exporter.export_pptx_to_pdf(str(pptx_file), pdf_path)
                if pdf_result:
                    download_path = artifact_storage.save_pdf(deck_id, pdf_path)
                    results["pdf"] = download_path
                else:
                    results["pdf"] = None
            except Exception as e:
                logger.error(f"PDF export error: {e}")
                results["pdf"] = None
        else:
            results["pdf"] = None
    
    return {
        "status": "exported",
        "deck_id": deck_id,
        "formats": results
    }


@router.get("/{deck_id}/download/{format}")
@api_router.get("/{deck_id}/download/{format}")
async def download_artifact(deck_id: str, format: str):
    """Download exported artifact"""
    from fastapi.responses import FileResponse
    from app.services.slide_studio.store.artifact import artifact_storage
    
    if format == "pptx":
        file_path = artifact_storage.get_pptx_path(deck_id)
        if not file_path or not file_path.exists():
            raise HTTPException(status_code=404, detail="PPTX file not found")
        return FileResponse(
            path=str(file_path),
            filename=f"{deck_id}.pptx",
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
    elif format == "pdf":
        file_path = artifact_storage.get_pdf_path(deck_id)
        if not file_path or not file_path.exists():
            raise HTTPException(status_code=404, detail="PDF file not found")
        return FileResponse(
            path=str(file_path),
            filename=f"{deck_id}.pdf",
            media_type="application/pdf"
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid format")


class SaveRequest(BaseModel):
    """Save version request"""
    label: Optional[str] = Field(None, description="Optional version label")


@router.post("/{deck_id}/save")
@api_router.post("/{deck_id}/save")
async def save_version(deck_id: str, request: SaveRequest):
    """Save current deck state as version"""
    deck_ir = slide_studio_repo.get_deck_ir(deck_id)
    if not deck_ir:
        raise HTTPException(status_code=404, detail="Deck not found")
    
    from app.services.slide_studio.ir.versioning import version_manager
    version_id = version_manager.save_version(deck_id, deck_ir, request.label)
    
    return {
        "status": "saved",
        "deck_id": deck_id,
        "version_id": version_id,
        "label": request.label or f"v{len(version_manager.get_versions(deck_id))}"
    }


@router.get("/{deck_id}/versions")
@api_router.get("/{deck_id}/versions")
async def get_versions(deck_id: str):
    """Get all versions for deck"""
    from app.services.slide_studio.ir.versioning import version_manager
    versions = version_manager.get_versions(deck_id)
    
    return {
        "deck_id": deck_id,
        "versions": versions
    }


@router.post("/{deck_id}/restore/{version_id}")
@api_router.post("/{deck_id}/restore/{version_id}")
async def restore_version(deck_id: str, version_id: str):
    """Restore deck to specific version"""
    from app.services.slide_studio.ir.versioning import version_manager
    
    # Save current state as version before restore
    current_deck_ir = slide_studio_repo.get_deck_ir(deck_id)
    if current_deck_ir:
        version_manager.save_version(deck_id, current_deck_ir, "pre-restore")
    
    # Restore version
    restored_ir = version_manager.restore_version(deck_id, version_id)
    if not restored_ir:
        raise HTTPException(status_code=404, detail="Version not found")
    
    # Update deck IR
    slide_studio_repo.save_deck_ir(restored_ir)
    
    return {
        "status": "restored",
        "deck_id": deck_id,
        "version_id": version_id
    }


class PatchElementRequest(BaseModel):
    """Patch element request"""
    bbox: Optional[Dict[str, float]] = None
    style: Optional[Dict[str, Any]] = None
    content: Optional[str] = None


@router.patch("/{deck_id}/slides/{slide_id}/elements/{element_id}")
@api_router.patch("/{deck_id}/slides/{slide_id}/elements/{element_id}")
async def patch_element(
    deck_id: str,
    slide_id: str,
    element_id: str,
    request: PatchElementRequest
):
    """Patch element (bbox, style, content)"""
    deck_ir = slide_studio_repo.get_deck_ir(deck_id)
    if not deck_ir:
        raise HTTPException(status_code=404, detail="Deck not found")
    
    # Find slide
    slide_ir = None
    for slide in deck_ir.slides:
        if slide.slide_id == slide_id:
            slide_ir = slide
            break
    
    if not slide_ir:
        raise HTTPException(status_code=404, detail="Slide not found")
    
    # Find element (slot)
    if element_id not in slide_ir.slots:
        raise HTTPException(status_code=404, detail="Element not found")
    
    slot = slide_ir.slots[element_id]
    
    # Apply patches
    if request.bbox:
        from app.services.slide_studio.ir.schema import BBox
        slot.bbox = BBox(**request.bbox)
    
    if request.style:
        from app.services.slide_studio.ir.schema import Style
        if slot.style:
            slot.style = slot.style.model_copy(update=request.style)
        else:
            slot.style = Style(**request.style)
    
    if request.content and hasattr(slot, 'content'):
        slot.content = request.content
    
    # Save updated deck IR
    slide_studio_repo.save_deck_ir(deck_ir)
    
    return {
        "status": "patched",
        "deck_id": deck_id,
        "slide_id": slide_id,
        "element_id": element_id
    }


class ReflowRequest(BaseModel):
    """Reflow request"""
    scope: str = Field("deck", description="Scope: deck or slide")
    slide_id: Optional[str] = Field(None, description="Slide ID (if scope is slide)")


@router.post("/{deck_id}/reflow")
@api_router.post("/{deck_id}/reflow")
async def reflow_layout(deck_id: str, request: ReflowRequest):
    """Recalculate layout"""
    deck_ir = slide_studio_repo.get_deck_ir(deck_id)
    if not deck_ir:
        raise HTTPException(status_code=404, detail="Deck not found")
    
    from app.services.slide_studio.layout.engine import layout_engine
    
    if request.scope == "slide" and request.slide_id:
        # Reflow single slide
        for slide in deck_ir.slides:
            if slide.slide_id == request.slide_id:
                layout_engine.layout_slide(slide)
                break
    else:
        # Reflow all slides
        for slide in deck_ir.slides:
            layout_engine.layout_slide(slide)
    
    slide_studio_repo.save_deck_ir(deck_ir)
    
    return {
        "status": "reflowed",
        "deck_id": deck_id
    }


@router.post("/{deck_id}/fact-check")
@api_router.post("/{deck_id}/fact-check")
async def fact_check_deck(deck_id: str, documents: List[str] = None):
    """Fact check deck"""
    deck_ir = slide_studio_repo.get_deck_ir(deck_id)
    if not deck_ir:
        raise HTTPException(status_code=404, detail="Deck not found")
    
    from app.services.slide_studio.fact_check import fact_checker
    result = await fact_checker.check_deck(deck_ir, documents)
    
    return result


@router.post("/{deck_id}/slides/{slide_id}/fact-check")
@api_router.post("/{deck_id}/slides/{slide_id}/fact-check")
async def fact_check_slide(deck_id: str, slide_id: str, documents: List[str] = None):
    """Fact check single slide"""
    deck_ir = slide_studio_repo.get_deck_ir(deck_id)
    if not deck_ir:
        raise HTTPException(status_code=404, detail="Deck not found")
    
    slide_ir = None
    for slide in deck_ir.slides:
        if slide.slide_id == slide_id:
            slide_ir = slide
            break
    
    if not slide_ir:
        raise HTTPException(status_code=404, detail="Slide not found")
    
    from app.services.slide_studio.fact_check import fact_checker
    result = await fact_checker.check_slide(slide_ir, documents)
    
    return result


# Static file serving for fonts
import os
from fastapi.responses import FileResponse

@router.get("/assets/fonts/{font_family}/{filename}")
@api_router.get("/assets/fonts/{font_family}/{filename}")
async def serve_font(font_family: str, filename: str):
    """Serve font files"""
    font_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "services",
        "slide_studio",
        "assets",
        "fonts",
        font_family,
        filename
    )
    font_path = os.path.abspath(font_path)
    
    if not os.path.exists(font_path):
        raise HTTPException(status_code=404, detail="Font file not found")
    
    return FileResponse(
        font_path,
        media_type="font/woff2" if filename.endswith(".woff2") else "font/woff",
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "Access-Control-Allow-Origin": "*"
        }
    )
