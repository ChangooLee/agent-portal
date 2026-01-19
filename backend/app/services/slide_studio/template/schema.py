"""Template Schema - Layout template definitions"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from app.services.slide_studio.ir.schema import SlideType


class GridConfig(BaseModel):
    """Grid system configuration"""
    columns: int = 12  # 12-column grid
    gutter: int = 16  # Gutter size in pixels
    margin: int = 24  # Outer margin in pixels


class SlotLayout(BaseModel):
    """Layout rules for a slot"""
    slot_id: str
    grid_column_start: int  # Start column (1-based)
    grid_column_span: int  # Column span
    grid_row_start: int  # Start row (1-based)
    grid_row_span: int  # Row span
    min_width: Optional[int] = None
    min_height: Optional[int] = None
    max_width: Optional[int] = None
    max_height: Optional[int] = None


class TypographyStyle(BaseModel):
    """Typography style for a text level"""
    font_size: int
    font_weight: str = "400"
    line_height: float = 1.5
    color: str = "#1f2937"


class SpacingRules(BaseModel):
    """Spacing rules for template"""
    slot_gap: int = 16  # Gap between slots
    section_margin: int = 32  # Margin between sections
    content_padding: int = 24  # Padding inside content area


class DecorativeElement(BaseModel):
    """Decorative element (line, shape, etc.)"""
    element_type: str  # "line", "shape", "icon"
    position: Dict[str, int]  # x, y, width, height
    style: Dict[str, str]  # CSS-like style properties


class LayoutTemplate(BaseModel):
    """Layout template for a slide type"""
    template_id: str = Field(..., description="Unique template ID")
    slide_type: SlideType = Field(..., description="Slide type this template is for")
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    grid: GridConfig = Field(default_factory=GridConfig)
    slot_layouts: Dict[str, SlotLayout] = Field(
        default_factory=dict,
        description="Slot layout rules (slot_id -> SlotLayout)"
    )
    typography_hierarchy: Dict[str, TypographyStyle] = Field(
        default_factory=dict,
        description="Typography hierarchy (title, body, caption, etc.)"
    )
    spacing_rules: SpacingRules = Field(default_factory=SpacingRules)
    decorative_elements: List[DecorativeElement] = Field(
        default_factory=list,
        description="Decorative elements"
    )
