"""Orchestrator Runner - Manages parallel SlideWorker execution"""
import asyncio
import logging
from typing import Dict, Optional, AsyncGenerator
from app.services.slide_studio.orchestrator.state import DeckState, SlideState
from app.services.slide_studio.orchestrator.events import (
    emit_slide_stage,
    emit_slide_finalized,
    emit_slide_issues,
    emit_slide_preview_updated,
    emit_job_error,
    emit_job_stopped
)
from app.services.slide_studio.ir.schema import SlideStage
from app.services.slide_studio.config import slide_studio_config

# Import singleton instances
from app.services.slide_studio.ir.builder import slide_builder
from app.services.slide_studio.layout.engine import layout_engine
from app.services.slide_studio.verify.heuristic import heuristic_verifier
from app.services.slide_studio.verify.metrics import quality_metrics_calculator
from app.services.slide_studio.verify.content import content_quality_verifier
from app.services.slide_studio.content.writer import content_writer
from app.services.slide_studio.fix.policies import reflection_policies
from app.services.slide_studio.fix.reflector import reflector
from app.services.slide_studio.fix.auto_fix import auto_fix
from app.services.slide_studio.preview.renderer import preview_renderer
from app.services.slide_studio.orchestrator.metrics import start_slide_span, inject_context_to_carrier
from app.services.agent_registry_service import AgentType

logger = logging.getLogger(__name__)


class SlideWorker:
    """Worker for processing a single slide"""
    
    def __init__(self, slide_state: SlideState, deck_state: DeckState):
        self.slide_state = slide_state
        self.deck_state = deck_state
    
    async def run(self) -> AsyncGenerator[str, None]:
        """
        Run slide generation pipeline.
        
        Yields:
            SSE event strings
        """
        # Get parent trace_id and root_carrier from deck_state
        parent_trace_id = self.deck_state.trace_id
        
        # Use root_carrier from deck_state to maintain trace context
        # If root_carrier is not available, create a new one from current context
        current_carrier = self.deck_state.root_carrier or {}
        if not current_carrier:
            inject_context_to_carrier(current_carrier)
        
        try:
            # DRAFTING
            with start_slide_span(
                name="gen_ai.agent.slide_drafting",
                attributes={
                    "slide.slide_id": self.slide_state.slide_id,
                    "slide.slide_type": self.slide_state.slide_plan.slide_type.value,
                    "slide.stage": SlideStage.DRAFTING.value,
                    "agent.id": "slide-studio",
                    "agent.name": "Slide Studio Agent",
                    "agent.type": AgentType.SLIDES.value,
                },
                parent_carrier=current_carrier
            ) as span:
                # Update current_carrier with the new span's context for child spans
                inject_context_to_carrier(current_carrier)
                if self.deck_state.stopped:
                    yield emit_job_stopped(self.deck_state.deck_id)
                    return
                
                self.slide_state.update_stage(SlideStage.DRAFTING, 0.1, "Generating draft content")
                yield emit_slide_stage(
                    self.deck_state.deck_id,
                    self.slide_state.slide_id,
                    SlideStage.DRAFTING,
                    0.1,
                    "Generating draft content"
                )
                
                # Build slide IR
                logger.info(f"[{self.slide_state.slide_id}] DRAFTING: Building slide IR from plan")
                logger.debug(f"[{self.slide_state.slide_id}] SlidePlan: {self.slide_state.slide_plan.model_dump_json(indent=2)}")
                
                slide_ir = await slide_builder.build_slide(
                    self.slide_state.slide_plan,
                    goal=self.deck_state.goal,
                    audience=self.deck_state.audience,
                    tone=self.deck_state.tone,
                    trace_id=parent_trace_id
                )
            
                logger.info(f"[{self.slide_state.slide_id}] DRAFTING: Slide IR created with {len(slide_ir.slots)} slots")
                logger.debug(f"[{self.slide_state.slide_id}] SlideIR (draft): {slide_ir.model_dump_json(indent=2)}")
                if hasattr(span, 'set_attribute'):
                    span.set_attribute("slide.slot_count", len(slide_ir.slots))
                self.slide_state.ir = slide_ir
            
            # WRITING: Improve content quality
            with start_slide_span(
                name="gen_ai.agent.slide_writing",
                attributes={
                    "slide.slide_id": self.slide_state.slide_id,
                    "slide.slide_type": self.slide_state.slide_plan.slide_type.value,
                    "slide.stage": SlideStage.WRITING.value,
                    "agent.id": "slide-studio",
                    "agent.name": "Slide Studio Agent",
                    "agent.type": AgentType.SLIDES.value,
                },
                parent_carrier=current_carrier
            ) as span:
                # Update current_carrier with the new span's context for child spans
                inject_context_to_carrier(current_carrier)
                if self.deck_state.stopped:
                    yield emit_job_stopped(self.deck_state.deck_id)
                    return
                
                self.slide_state.update_stage(SlideStage.WRITING, 0.3, "Refining content")
                yield emit_slide_stage(
                    self.deck_state.deck_id,
                    self.slide_state.slide_id,
                    SlideStage.WRITING,
                    0.3,
                    "Refining content"
                )
                
                logger.info(f"[{self.slide_state.slide_id}] WRITING: Improving content quality")
                slide_ir = await content_writer.rewrite_for_slide(slide_ir, trace_id=parent_trace_id)
                self.slide_state.ir = slide_ir
                logger.info(f"[{self.slide_state.slide_id}] WRITING: Content rewritten, {len(slide_ir.slots)} slots")
            
            # LAYOUTING
            with start_slide_span(
                name="gen_ai.agent.slide_layouting",
                attributes={
                    "slide.slide_id": self.slide_state.slide_id,
                    "slide.slide_type": self.slide_state.slide_plan.slide_type.value,
                    "slide.stage": SlideStage.LAYOUTING.value,
                    "agent.id": "slide-studio",
                    "agent.name": "Slide Studio Agent",
                    "agent.type": AgentType.SLIDES.value,
                },
                parent_carrier=current_carrier
            ) as span:
                # Update current_carrier with the new span's context for child spans
                inject_context_to_carrier(current_carrier)
                if self.deck_state.stopped:
                    yield emit_job_stopped(self.deck_state.deck_id)
                    return
                
                self.slide_state.update_stage(SlideStage.LAYOUTING, 0.4, "Calculating layout")
                yield emit_slide_stage(
                    self.deck_state.deck_id,
                    self.slide_state.slide_id,
                    SlideStage.LAYOUTING,
                    0.4,
                    "Calculating layout"
                )
                
                # Select template and calculate layout
                from app.services.slide_studio.template.selector import template_selector
                selected_template = template_selector.select_template(
                    self.slide_state.slide_plan.slide_type,
                    slide_ir,
                    trace_id=parent_trace_id
                )
                if hasattr(span, 'set_attribute'):
                    span.set_attribute("slide.template_id", selected_template.template_id)
                logger.debug(f"[{self.slide_state.slide_id}] LAYOUTING: Selected template: {selected_template.template_id}")
                
                # Calculate layout (template-based)
                logger.info(f"[{self.slide_state.slide_id}] LAYOUTING: Calculating layout with template")
                slide_ir = layout_engine.layout_slide(
                    slide_ir,
                    selected_template,
                    self.deck_state.theme_id,
                    self.deck_state.theme_variant_map
                )
                self.slide_state.ir = slide_ir
                logger.info(f"[{self.slide_state.slide_id}] LAYOUTING: Layout calculated, bboxes assigned")
            
            # Save to deck IR
            from app.services.slide_studio.store.repo import slide_studio_repo
            deck_ir = slide_studio_repo.get_deck_ir(self.deck_state.deck_id)
            if deck_ir:
                # Update slide in deck IR
                for i, s in enumerate(deck_ir.slides):
                    if s.slide_id == slide_ir.slide_id:
                        deck_ir.slides[i] = slide_ir
                        break
                else:
                    deck_ir.slides.append(slide_ir)
                slide_studio_repo.save_deck_ir(deck_ir)
            
            await asyncio.sleep(0.2)
            
            # VERIFYING (with reflection loop)
            reflection_done = False
            while not reflection_done:
                with start_slide_span(
                    name="gen_ai.agent.slide_verifying",
                    attributes={
                        "slide.slide_id": self.slide_state.slide_id,
                        "slide.slide_type": self.slide_state.slide_plan.slide_type.value,
                        "slide.stage": SlideStage.VERIFYING.value,
                        "slide.reflection_count": self.slide_state.reflection_count,
                        "agent.id": "slide-studio",
                        "agent.name": "Slide Studio Agent",
                        "agent.type": AgentType.SLIDES.value,
                    },
                    parent_carrier=current_carrier
                ) as span:
                    if self.deck_state.stopped:
                        yield emit_job_stopped(self.deck_state.deck_id)
                        return
                    
                    self.slide_state.update_stage(SlideStage.VERIFYING, 0.7, "Verifying quality")
                    yield emit_slide_stage(
                        self.deck_state.deck_id,
                        self.slide_state.slide_id,
                        SlideStage.VERIFYING,
                        0.7,
                        "Verifying quality"
                    )
                    
                    # Verify (with optional Playwright)
                    use_playwright = getattr(self.deck_state, 'use_playwright', False)
                    logger.info(f"[{self.slide_state.slide_id}] VERIFYING: Running verification (playwright={use_playwright})")
                    issues = heuristic_verifier.verify_slide(slide_ir, use_playwright=use_playwright)
                    slide_ir.issues = issues
                    logger.info(f"[{self.slide_state.slide_id}] VERIFYING: Found {len(issues)} issues")
                    for issue in issues:
                        logger.debug(f"[{self.slide_state.slide_id}] Issue: {issue.get('type')} - {issue.get('message')} (severity: {issue.get('severity')})")
                    
                    # Calculate metrics and score
                    metrics = quality_metrics_calculator.calculate_metrics(slide_ir)
                    logger.info(f"[{self.slide_state.slide_id}] VERIFYING: Metrics calculated - overflow: {metrics.overflow_count}, overlap: {metrics.overlap_count}, margin_violations: {metrics.margin_violation_count}, min_font: {metrics.min_font_size}")
                    
                    # Add content quality penalties
                    content_quality = content_quality_verifier.verify_content_quality(slide_ir)
                    logger.info(f"[{self.slide_state.slide_id}] VERIFYING: Content quality - clarity: {content_quality.get('clarity_score', 100)}, structure: {content_quality.get('structure_score', 100)}, redundancy: {content_quality.get('redundancy_score', 100)}, specificity: {content_quality.get('specificity_score', 100)}")
                    
                    score = quality_metrics_calculator.calculate_score(metrics)
                    logger.info(f"[{self.slide_state.slide_id}] VERIFYING: Base score: {score}")
                    
                    # Apply content quality penalties
                    clarity_penalty = 0
                    structure_penalty = 0
                    redundancy_penalty = 0
                    specificity_penalty = 0
                    
                    if content_quality.get("clarity_score", 100) < 80:
                        clarity_penalty = 10.0
                        score -= clarity_penalty
                        logger.info(f"[{self.slide_state.slide_id}] VERIFYING: Clarity penalty: -{clarity_penalty} (score: {content_quality.get('clarity_score', 100)})")
                    if content_quality.get("structure_score", 100) < 80:
                        structure_penalty = 8.0
                        score -= structure_penalty
                        logger.info(f"[{self.slide_state.slide_id}] VERIFYING: Structure penalty: -{structure_penalty} (score: {content_quality.get('structure_score', 100)})")
                    if content_quality.get("redundancy_score", 100) < 90:
                        redundancy_penalty = 5.0
                        score -= redundancy_penalty
                        logger.info(f"[{self.slide_state.slide_id}] VERIFYING: Redundancy penalty: -{redundancy_penalty} (score: {content_quality.get('redundancy_score', 100)})")
                    if content_quality.get("specificity_score", 100) < 80:
                        specificity_penalty = 5.0
                        score -= specificity_penalty
                        logger.info(f"[{self.slide_state.slide_id}] VERIFYING: Specificity penalty: -{specificity_penalty} (score: {content_quality.get('specificity_score', 100)})")
                    
                    # Add content quality issues to issues list
                    issues.extend(content_quality.get("issues", []))
                    
                    score = max(0.0, min(100.0, score))
                    slide_ir.metrics = metrics
                    slide_ir.score = score
                    self.slide_state.score = score
                    self.slide_state.issues = issues
                    logger.info(f"[{self.slide_state.slide_id}] VERIFYING: Final score: {score} (penalties: clarity={clarity_penalty}, structure={structure_penalty}, redundancy={redundancy_penalty}, specificity={specificity_penalty})")
                    
                    # Set span attributes before emitting
                    if hasattr(span, 'set_attribute'):
                        span.set_attribute("slide.score", score)
                        span.set_attribute("slide.issues_count", len(issues))
                        span.set_attribute("slide.reflection_count", self.slide_state.reflection_count)
                        span.set_attribute("slide.overflow_count", metrics.overflow_count)
                        span.set_attribute("slide.overlap_count", metrics.overlap_count)
                        span.set_attribute("slide.margin_violation_count", metrics.margin_violation_count)
                        if metrics.min_font_size:
                            span.set_attribute("slide.min_font_size", metrics.min_font_size)
                    
                    # Emit issues
                    yield emit_slide_issues(
                        self.deck_state.deck_id,
                        self.slide_state.slide_id,
                        issues,
                        score,
                        metrics.model_dump()
                    )
                    
                    # Check if should reflect
                    should_reflect = reflection_policies.should_reflect(
                        slide_ir,
                        metrics,
                        score,
                        self.slide_state.reflection_count
                    )
                    
                    logger.info(f"[{self.slide_state.slide_id}] VERIFYING: Should reflect: {should_reflect} (reflection_count: {self.slide_state.reflection_count}, score: {score}, error_issues: {len([i for i in issues if i.get('severity') == 'error'])})")
                
                # Check if should reflect (outside span to allow proper control flow)
                if should_reflect:
                    # REFLECTING
                    with start_slide_span(
                            name="gen_ai.agent.slide_reflecting",
                            attributes={
                                "slide.slide_id": self.slide_state.slide_id,
                                "slide.slide_type": self.slide_state.slide_plan.slide_type.value,
                                "slide.stage": SlideStage.REFLECTING.value,
                                "slide.reflection_count": self.slide_state.reflection_count + 1,
                                "agent.id": "slide-studio",
                                "agent.name": "Slide Studio Agent",
                                "agent.type": AgentType.SLIDES.value,
                            },
                        parent_carrier=current_carrier
                    ) as reflect_span:
                        if self.deck_state.stopped:
                            yield emit_job_stopped(self.deck_state.deck_id)
                            return
                        
                        self.slide_state.increment_reflection()
                        self.slide_state.update_stage(SlideStage.REFLECTING, 0.75, "Analyzing and fixing issues")
                        yield emit_slide_stage(
                            self.deck_state.deck_id,
                            self.slide_state.slide_id,
                            SlideStage.REFLECTING,
                            0.75,
                            "Analyzing and fixing issues"
                        )
                        
                        # Reflect and get suggestions
                        logger.info(f"[{self.slide_state.slide_id}] REFLECTING: Analyzing {len(issues)} issues")
                        suggestions = await reflector.reflect(slide_ir, issues, trace_id=parent_trace_id)
                        logger.info(f"[{self.slide_state.slide_id}] REFLECTING: Suggestions - {len(suggestions.get('actions', []))} actions, reasoning: {suggestions.get('reasoning', '')[:100]}")
                        
                        # Set span attributes
                        if hasattr(reflect_span, 'set_attribute'):
                            reflect_span.set_attribute("slide.reflection_count", self.slide_state.reflection_count)
                            reflect_span.set_attribute("slide.issues_count", len(issues))
                            reflect_span.set_attribute("slide.suggestions_count", len(suggestions.get('actions', [])))
                        
                        # Apply fixes (may include LLM-based regeneration)
                        if suggestions.get("actions"):
                            fix_action = suggestions["actions"][0]
                            fix_type = fix_action.get("type", "shorten_text")
                            target_slot = fix_action.get("target")
                            logger.info(f"[{self.slide_state.slide_id}] REFLECTING: Applying fix - type: {fix_type}, target: {target_slot}")
                            
                            # Check if we need to regenerate with LLM
                            if fix_type in ["regenerate", "rewrite", "improve_content"]:
                                logger.info(f"[{self.slide_state.slide_id}] REFLECTING: LLM regeneration required (fix_type: {fix_type})")
                                # DRAFTING (부분 재생성) - 문서 요구사항에 따라
                                self.slide_state.update_stage(SlideStage.DRAFTING, 0.76, "Regenerating content with improvements")
                                yield emit_slide_stage(
                                    self.deck_state.deck_id,
                                    self.slide_state.slide_id,
                                    SlideStage.DRAFTING,
                                    0.76,
                                    "Regenerating content with improvements"
                                )
                                
                                # Rebuild slide with LLM (passing issues for context)
                                logger.info(f"[{self.slide_state.slide_id}] REFLECTING: Calling LLM for improvement with {len(issues)} issues")
                                improved_slide_ir = await slide_builder.build_slide_with_improvements(
                                    self.slide_state.slide_plan,
                                    slide_ir,
                                    issues,
                                    suggestions.get("reasoning", ""),
                                    goal=self.deck_state.goal,
                                    audience=self.deck_state.audience,
                                    tone=self.deck_state.tone,
                                    trace_id=parent_trace_id
                                )
                                
                                if improved_slide_ir:
                                    logger.info(f"[{self.slide_state.slide_id}] REFLECTING: LLM regeneration successful, {len(improved_slide_ir.slots)} slots")
                                    slide_ir = improved_slide_ir
                                    self.slide_state.ir = slide_ir
                                else:
                                    logger.warning(f"[{self.slide_state.slide_id}] REFLECTING: LLM regeneration failed, falling back to auto_fix")
                                    # Fallback to auto_fix if LLM regeneration fails
                                    slide_ir = auto_fix.apply_fix(slide_ir, fix_type, target_slot)
                                    self.slide_state.ir = slide_ir
                            else:
                                # Simple fixes (shorten_text, adjust_layout, etc.)
                                logger.info(f"[{self.slide_state.slide_id}] REFLECTING: Applying simple fix (type: {fix_type})")
                                slide_ir = auto_fix.apply_fix(slide_ir, fix_type, target_slot)
                                self.slide_state.ir = slide_ir
                    
                    # Re-layout after fix (문서 요구사항: REFLECTING → DRAFTING → LAYOUTING)
                    self.slide_state.update_stage(SlideStage.LAYOUTING, 0.77, "Recalculating layout after fix")
                    yield emit_slide_stage(
                        self.deck_state.deck_id,
                        self.slide_state.slide_id,
                        SlideStage.LAYOUTING,
                        0.77,
                        "Recalculating layout after fix"
                    )
                    
                    # Re-select template and re-layout
                    from app.services.slide_studio.template.selector import template_selector
                    selected_template = template_selector.select_template(
                        self.slide_state.slide_plan.slide_type,
                        slide_ir,
                        trace_id=parent_trace_id
                    )
                    slide_ir = layout_engine.layout_slide(
                        slide_ir,
                        selected_template,
                        self.deck_state.theme_id,
                        self.deck_state.theme_variant_map
                    )
                    self.slide_state.ir = slide_ir
                    
                    # Save to deck IR
                    from app.services.slide_studio.store.repo import slide_studio_repo
                    deck_ir = slide_studio_repo.get_deck_ir(self.deck_state.deck_id)
                    if deck_ir:
                        for i, s in enumerate(deck_ir.slides):
                            if s.slide_id == slide_ir.slide_id:
                                deck_ir.slides[i] = slide_ir
                                break
                        else:
                            deck_ir.slides.append(slide_ir)
                        slide_studio_repo.save_deck_ir(deck_ir)
                    
                    await asyncio.sleep(0.2)
                    # Continue loop to verify again after fix
                else:
                    reflection_done = True
            
            # Check if should finalize with warnings
            should_finalize_with_warnings = reflection_policies.should_finalize_with_warnings(
                slide_ir,
                metrics,
                score,
                self.slide_state.reflection_count
            )
            
            await asyncio.sleep(0.1)
            
            # PREVIEW_RENDERING
            with start_slide_span(
                name="gen_ai.agent.slide_preview_rendering",
                attributes={
                    "slide.slide_id": self.slide_state.slide_id,
                    "slide.slide_type": self.slide_state.slide_plan.slide_type.value,
                    "slide.stage": SlideStage.PREVIEW_RENDERING.value,
                    "agent.id": "slide-studio",
                    "agent.name": "Slide Studio Agent",
                    "agent.type": AgentType.SLIDES.value,
                },
                parent_carrier=current_carrier
            ) as span:
                if self.deck_state.stopped:
                    yield emit_job_stopped(self.deck_state.deck_id)
                    return
                
                self.slide_state.update_stage(SlideStage.PREVIEW_RENDERING, 0.8, "Rendering preview")
                yield emit_slide_stage(
                    self.deck_state.deck_id,
                    self.slide_state.slide_id,
                    SlideStage.PREVIEW_RENDERING,
                    0.8,
                    "Rendering preview"
                )
                
                # Render preview
                html_preview = preview_renderer.render_html(slide_ir)
                
                # Set span attributes
                if hasattr(span, 'set_attribute'):
                    span.set_attribute("slide.preview_html_size", len(html_preview))
                
                # Emit preview updated (with HTML data URI for now)
                import base64
                html_base64 = base64.b64encode(html_preview.encode('utf-8')).decode('utf-8')
                yield emit_slide_preview_updated(
                    self.deck_state.deck_id,
                    self.slide_state.slide_id,
                    thumbnail_data_uri=f"data:text/html;base64,{html_base64}"
                )
            
            await asyncio.sleep(0.1)
            
            # FINAL or FINAL_WITH_WARNINGS
            # Prepare attributes (avoid None values)
            final_attrs = {
                "slide.slide_id": self.slide_state.slide_id,
                "slide.slide_type": self.slide_state.slide_plan.slide_type.value,
                "slide.stage": SlideStage.FINAL.value,
                "slide.final_issues_count": len(self.slide_state.issues),
                "slide.final_reflection_count": self.slide_state.reflection_count,
                "agent.id": "slide-studio",
                "agent.name": "Slide Studio Agent",
                "agent.type": AgentType.SLIDES.value,
            }
            if self.slide_state.score is not None:
                final_attrs["slide.final_score"] = self.slide_state.score
            
            with start_slide_span(
                name="gen_ai.agent.slide_finalizing",
                attributes=final_attrs,
                parent_carrier=current_carrier
            ) as span:
                if self.deck_state.stopped:
                    yield emit_job_stopped(self.deck_state.deck_id)
                    return
                
                final_stage = SlideStage.FINAL_WITH_WARNINGS if should_finalize_with_warnings else SlideStage.FINAL
                self.slide_state.update_stage(final_stage, 1.0, "Completed")
                logger.info(f"[{self.slide_state.slide_id}] FINALIZED: Slide generation completed with stage: {final_stage.value}, score: {score:.2f}")
                
                # Set final span attributes
                if hasattr(span, 'set_attribute'):
                    span.set_attribute("slide.final_stage", final_stage.value)
                    if self.slide_state.score is not None:
                        span.set_attribute("slide.final_score", self.slide_state.score)
                    span.set_attribute("slide.final_issues_count", len(self.slide_state.issues))
                    span.set_attribute("slide.final_reflection_count", self.slide_state.reflection_count)
                    if metrics:
                        span.set_attribute("slide.native_text_ratio", metrics.native_text_ratio)
                        span.set_attribute("slide.editability_estimate", metrics.native_text_ratio)
                
                yield emit_slide_stage(
                    self.deck_state.deck_id,
                    self.slide_state.slide_id,
                    final_stage,
                    1.0,
                    "Completed"
                )
                
                yield emit_slide_finalized(
                    self.deck_state.deck_id,
                    self.slide_state.slide_id,
                    score=score,
                    editability_estimate=metrics.native_text_ratio if metrics else 0.8
                )
        
        except Exception as e:
            logger.error(f"SlideWorker error for {self.slide_state.slide_id}: {e}", exc_info=True)
            self.slide_state.update_stage(SlideStage.ERROR, 0.0, str(e))
            yield emit_job_error("slide", self.slide_state.slide_id, str(e))


class Orchestrator:
    """Orchestrates parallel slide generation"""
    
    def __init__(self, deck_state: DeckState):
        self.deck_state = deck_state
        self.semaphore = asyncio.Semaphore(slide_studio_config.MAX_CONCURRENT_SLIDES)
        self.workers: Dict[str, SlideWorker] = {}
    
    async def run_all_slides(self, parent_trace_id: Optional[str] = None) -> AsyncGenerator[str, None]:
        """
        Run all slides in parallel with concurrency control.
        
        Yields:
            SSE event strings from all workers (interleaved)
        """
        # Create workers for all slides
        for slide_id, slide_state in self.deck_state.slides.items():
            self.workers[slide_id] = SlideWorker(slide_state, self.deck_state)
        
        # Use a queue to interleave events from all workers
        event_queue = asyncio.Queue()
        
        async def run_worker_with_semaphore(worker: SlideWorker):
            """Run worker with semaphore and put events in queue"""
            async with self.semaphore:
                try:
                    async for event in worker.run():
                        await event_queue.put(event)
                except Exception as e:
                    logger.error(f"Worker error: {e}")
                finally:
                    await event_queue.put(None)  # Sentinel to mark completion
        
        # Start all workers
        tasks = [
            asyncio.create_task(run_worker_with_semaphore(worker))
            for worker in self.workers.values()
        ]
        
        # Yield events as they arrive
        completed = 0
        total_workers = len(tasks)
        
        while completed < total_workers:
            event = await event_queue.get()
            if event is None:
                completed += 1
            else:
                yield event
        
        # Wait for all tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)
