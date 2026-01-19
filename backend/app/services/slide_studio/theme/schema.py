"""Theme Schema - Theme and Background Variant definitions"""
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class TypographyConfig(BaseModel):
    """Typography configuration for theme"""
    heading_font: str = "Pretendard"
    body_font: str = "Pretendard"
    font_scale: float = 1.0  # Scale factor for font sizes


class SpacingConfig(BaseModel):
    """Spacing configuration for theme"""
    grid_size: int = 8
    margin_base: int = 24
    padding_base: int = 16


class BackgroundVariant(BaseModel):
    """Background variant for a slide type"""
    variant_id: str = Field(..., description="Unique variant ID")
    type: Literal["solid", "gradient", "pattern", "image"] = Field(..., description="Background type")
    css: str = Field(..., description="CSS background property")
    pptx_image_path: Optional[str] = Field(None, description="PNG path for PPTX export")
    tone_tags: List[str] = Field(default_factory=list, description="Tone tags: formal, casual, professional, etc.")


class Theme(BaseModel):
    """Theme definition"""
    theme_id: str = Field(..., description="Unique theme ID")
    name: str = Field(..., description="Theme name")
    description: str = Field(..., description="Theme description")
    palette: Dict[str, str] = Field(..., description="Color palette: primary, secondary, accent, text, bg")
    background_variants: Dict[str, List[BackgroundVariant]] = Field(
        ..., 
        description="Background variants by slide_type"
    )
    typography: TypographyConfig = Field(default_factory=TypographyConfig)
    spacing: SpacingConfig = Field(default_factory=SpacingConfig)
