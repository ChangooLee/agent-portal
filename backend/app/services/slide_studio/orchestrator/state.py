"""Deck and Slide State Management"""
from typing import Dict, Optional, List
from datetime import datetime
from app.services.slide_studio.ir.schema import DeckIR, SlideIR, SlideStage


class DeckState:
    """Deck state for orchestration"""
    
    def __init__(self, deck_id: str, title: str, theme_id: Optional[str] = None, theme_variant_map: Optional[Dict[str, str]] = None, trace_id: Optional[str] = None, goal: Optional[str] = None, audience: Optional[str] = None, tone: Optional[str] = None, root_carrier: Optional[Dict[str, str]] = None):
        self.deck_id = deck_id
        self.title = title
        self.ir: Optional[DeckIR] = None
        self.slides: Dict[str, 'SlideState'] = {}
        self.status: str = "generating"  # generating, ready, exporting, error
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.stopped: bool = False
        self.theme_id: Optional[str] = theme_id
        self.theme_variant_map: Dict[str, str] = theme_variant_map or {}
        self.trace_id: Optional[str] = trace_id
        self.goal: Optional[str] = goal
        self.audience: Optional[str] = audience
        self.tone: Optional[str] = tone
        self.root_carrier: Optional[Dict[str, str]] = root_carrier  # OTEL context carrier for trace propagation
    
    def add_slide(self, slide_id: str, slide_state: 'SlideState'):
        """Add a slide state"""
        self.slides[slide_id] = slide_state
        self.updated_at = datetime.now()
    
    def get_slide(self, slide_id: str) -> Optional['SlideState']:
        """Get slide state by ID"""
        return self.slides.get(slide_id)
    
    def all_slides_finalized(self) -> bool:
        """Check if all slides are finalized"""
        if not self.slides:
            return False
        return all(
            slide.stage in (SlideStage.FINAL, SlideStage.FINAL_WITH_WARNINGS, SlideStage.ERROR, SlideStage.STOPPED)
            for slide in self.slides.values()
        )


class SlideState:
    """Slide state for orchestration"""
    
    def __init__(self, slide_id: str, slide_plan):
        self.slide_id = slide_id
        self.slide_plan = slide_plan
        self.ir: Optional[SlideIR] = None
        self.stage: SlideStage = SlideStage.PLANNED
        self.progress: float = 0.0  # 0.0 to 1.0
        self.message: str = ""
        self.score: Optional[float] = None
        self.issues: List[Dict] = []
        self.reflection_count: int = 0
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def update_stage(self, stage: SlideStage, progress: float = None, message: str = ""):
        """Update slide stage"""
        self.stage = stage
        if progress is not None:
            self.progress = progress
        if message:
            self.message = message
        self.updated_at = datetime.now()
    
    def increment_reflection(self):
        """Increment reflection count"""
        self.reflection_count += 1
        self.updated_at = datetime.now()
