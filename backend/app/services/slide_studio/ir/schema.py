"""IR Schema Definitions (Pydantic Models)"""
from enum import Enum
from typing import Dict, List, Optional, Union, Any, Literal
from pydantic import BaseModel, Field, Discriminator
from datetime import datetime


class SlideStage(str, Enum):
    """Slide generation stage"""
    PLANNED = "PLANNED"
    DRAFTING = "DRAFTING"
    WRITING = "WRITING"
    LAYOUTING = "LAYOUTING"
    VERIFYING = "VERIFYING"
    REFLECTING = "REFLECTING"
    PREVIEW_RENDERING = "PREVIEW_RENDERING"
    FINAL = "FINAL"
    ERROR = "ERROR"
    STOPPED = "STOPPED"
    FINAL_WITH_WARNINGS = "FINAL_WITH_WARNINGS"


class SlideType(str, Enum):
    """Slide type"""
    TITLE = "TITLE"
    AGENDA = "AGENDA"
    TWO_COLUMN = "TWO_COLUMN"
    BULLET = "BULLET"
    IMAGE = "IMAGE"
    CHART = "CHART"
    TABLE = "TABLE"
    SECTION = "SECTION"


class ExportStrategy(str, Enum):
    """Export strategy for slots"""
    NATIVE = "NATIVE"  # Native PowerPoint element (editable)
    IMAGE = "IMAGE"  # Rendered as image


class BBox(BaseModel):
    """Bounding box (position and size)"""
    x: float = Field(..., description="X position in pixels")
    y: float = Field(..., description="Y position in pixels")
    w: float = Field(..., description="Width in pixels")
    h: float = Field(..., description="Height in pixels")


class Style(BaseModel):
    """Element style"""
    font_family: Optional[str] = Field(None, description="Font family")
    font_size: Optional[int] = Field(None, description="Font size in pixels")
    font_weight: Optional[str] = Field(None, description="Font weight (normal, bold, etc.)")
    color: Optional[str] = Field(None, description="Text color (hex)")
    background_color: Optional[str] = Field(None, description="Background color (hex)")
    align: Optional[str] = Field(None, description="Text alignment (left, center, right)")
    line_height: Optional[float] = Field(None, description="Line height multiplier")


# Slot types (complete for Step 2)
class TextSlot(BaseModel):
    """Text slot"""
    slot_type: Literal["text"] = "text"
    content: str = Field(..., description="Text content")
    bbox: Optional[BBox] = None
    style: Optional[Style] = None
    export_strategy: ExportStrategy = ExportStrategy.NATIVE


class BulletSlot(BaseModel):
    """Bullet point slot"""
    slot_type: Literal["bullet"] = "bullet"
    items: List[str] = Field(..., description="Bullet point items")
    bbox: Optional[BBox] = None
    style: Optional[Style] = None
    export_strategy: ExportStrategy = ExportStrategy.NATIVE


class ImageSlot(BaseModel):
    """Image slot"""
    slot_type: Literal["image"] = "image"
    image_url: Optional[str] = Field(None, description="Image URL or path")
    alt_text: Optional[str] = Field(None, description="Alt text")
    bbox: Optional[BBox] = None
    export_strategy: ExportStrategy = ExportStrategy.IMAGE


class ChartSlot(BaseModel):
    """Chart slot"""
    slot_type: Literal["chart"] = "chart"
    chart_type: str = Field(..., description="Chart type (bar, line, pie, etc.)")
    data: Dict[str, Any] = Field(..., description="Chart data")
    bbox: Optional[BBox] = None
    export_strategy: ExportStrategy = ExportStrategy.IMAGE


class TableSlot(BaseModel):
    """Table slot"""
    slot_type: Literal["table"] = "table"
    headers: List[str] = Field(..., description="Table headers")
    rows: List[List[str]] = Field(..., description="Table rows")
    bbox: Optional[BBox] = None
    export_strategy: ExportStrategy = Field(
        ExportStrategy.NATIVE,
        description="Native for simple tables, IMAGE for complex"
    )


# Slot Union (discriminated union)
SlotUnion = Union[TextSlot, BulletSlot, ImageSlot, ChartSlot, TableSlot]


class SlidePlan(BaseModel):
    """Slide plan (from DeckPlanner)"""
    slide_id: str = Field(..., description="Unique slide ID")
    title: str = Field(..., description="Slide title")
    slide_type: SlideType = Field(..., description="Slide type")
    goal: Optional[str] = Field(None, description="Slide goal/objective")
    intent: Optional[str] = Field(None, description="Slide intent/purpose")
    key_message: Optional[str] = Field(None, description="Key message of the slide")
    supporting_points: List[str] = Field(default_factory=list, description="Supporting points/examples")
    data_placeholder: Optional[Dict[str, Any]] = Field(None, description="Data/number placeholders")


class QualityMetrics(BaseModel):
    """Quality metrics for a slide"""
    overflow_count: int = 0
    overlap_count: int = 0
    margin_violation_count: int = 0
    min_font_size: Optional[int] = None
    max_text_per_slide: Optional[int] = None
    native_text_ratio: float = 0.0  # Ratio of native text vs images


class SlideIR(BaseModel):
    """Slide IR (Intermediate Representation)"""
    slide_id: str = Field(..., description="Unique slide ID")
    title: str = Field(..., description="Slide title")
    slide_type: SlideType = Field(..., description="Slide type")
    slots: Dict[str, SlotUnion] = Field(
        default_factory=dict,
        description="Slots dictionary (slot_id -> Slot)"
    )
    stage: SlideStage = SlideStage.PLANNED
    score: Optional[float] = Field(None, description="Quality score (0-100)")
    issues: List[Dict[str, Any]] = Field(default_factory=list, description="Quality issues")
    metrics: Optional[QualityMetrics] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class DeckIR(BaseModel):
    """Deck IR (Intermediate Representation)"""
    deck_id: str = Field(..., description="Unique deck ID")
    theme_id: Optional[str] = Field(None, description="Selected theme ID")
    theme_variant_map: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of slide_type -> variant_id for background variants"
    )
    title: str = Field(..., description="Deck title")
    slides: List[SlideIR] = Field(default_factory=list, description="Slides in deck")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
