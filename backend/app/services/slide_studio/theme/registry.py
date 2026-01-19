"""Theme Registry - Predefined themes"""
from typing import Dict, List, Optional
from app.services.slide_studio.theme.schema import Theme, BackgroundVariant, TypographyConfig, SpacingConfig


class ThemeRegistry:
    """Registry of predefined themes"""
    
    def __init__(self):
        self._themes: Dict[str, Theme] = {}
        self._load_default_themes()
    
    def _load_default_themes(self):
        """Load default themes"""
        # Professional Theme
        professional = Theme(
            theme_id="professional",
            name="Professional",
            description="Clean, formal design suitable for business presentations",
            palette={
                "primary": "#1e40af",  # Blue
                "secondary": "#3b82f6",
                "accent": "#f59e0b",  # Amber
                "text": "#1f2937",  # Gray-800
                "bg": "#ffffff"  # White
            },
            background_variants={
                "TITLE": [
                    BackgroundVariant(
                        variant_id="solid_1",
                        type="solid",
                        css="background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);",
                        tone_tags=["formal", "professional"]
                    ),
                    BackgroundVariant(
                        variant_id="gradient_1",
                        type="gradient",
                        css="background: linear-gradient(135deg, #ffffff 0%, #e0e7ff 100%);",
                        tone_tags=["professional", "clean"]
                    )
                ],
                "BULLET": [
                    BackgroundVariant(
                        variant_id="solid_1",
                        type="solid",
                        css="background: #ffffff;",
                        tone_tags=["clean", "professional"]
                    ),
                    BackgroundVariant(
                        variant_id="gradient_1",
                        type="gradient",
                        css="background: linear-gradient(180deg, #ffffff 0%, #f3f4f6 100%);",
                        tone_tags=["professional"]
                    )
                ],
                "SECTION": [
                    BackgroundVariant(
                        variant_id="solid_1",
                        type="solid",
                        css="background: #ffffff;",
                        tone_tags=["clean"]
                    )
                ]
            },
            typography=TypographyConfig(
                heading_font="Pretendard",
                body_font="Pretendard",
                font_scale=1.0
            ),
            spacing=SpacingConfig(
                grid_size=8,
                margin_base=24,
                padding_base=16
            )
        )
        
        # Modern Theme
        modern = Theme(
            theme_id="modern",
            name="Modern",
            description="Contemporary design with vibrant colors",
            palette={
                "primary": "#6366f1",  # Indigo
                "secondary": "#8b5cf6",  # Purple
                "accent": "#ec4899",  # Pink
                "text": "#1f2937",
                "bg": "#ffffff"
            },
            background_variants={
                "TITLE": [
                    BackgroundVariant(
                        variant_id="gradient_1",
                        type="gradient",
                        css="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);",
                        tone_tags=["modern", "vibrant"]
                    )
                ],
                "BULLET": [
                    BackgroundVariant(
                        variant_id="solid_1",
                        type="solid",
                        css="background: #ffffff;",
                        tone_tags=["clean", "modern"]
                    )
                ],
                "SECTION": [
                    BackgroundVariant(
                        variant_id="solid_1",
                        type="solid",
                        css="background: #ffffff;",
                        tone_tags=["clean"]
                    )
                ]
            },
            typography=TypographyConfig(
                heading_font="Pretendard",
                body_font="Pretendard",
                font_scale=1.0
            ),
            spacing=SpacingConfig(
                grid_size=8,
                margin_base=24,
                padding_base=16
            )
        )
        
        # Minimal Theme
        minimal = Theme(
            theme_id="minimal",
            name="Minimal",
            description="Minimalist design with subtle colors",
            palette={
                "primary": "#374151",  # Gray-700
                "secondary": "#6b7280",  # Gray-500
                "accent": "#9ca3af",  # Gray-400
                "text": "#111827",  # Gray-900
                "bg": "#ffffff"
            },
            background_variants={
                "TITLE": [
                    BackgroundVariant(
                        variant_id="solid_1",
                        type="solid",
                        css="background: #ffffff;",
                        tone_tags=["minimal", "clean"]
                    )
                ],
                "BULLET": [
                    BackgroundVariant(
                        variant_id="solid_1",
                        type="solid",
                        css="background: #ffffff;",
                        tone_tags=["minimal"]
                    )
                ],
                "SECTION": [
                    BackgroundVariant(
                        variant_id="solid_1",
                        type="solid",
                        css="background: #ffffff;",
                        tone_tags=["minimal"]
                    )
                ]
            },
            typography=TypographyConfig(
                heading_font="Pretendard",
                body_font="Pretendard",
                font_scale=1.0
            ),
            spacing=SpacingConfig(
                grid_size=8,
                margin_base=32,
                padding_base=20
            )
        )
        
        self._themes["professional"] = professional
        self._themes["modern"] = modern
        self._themes["minimal"] = minimal
    
    def get_theme(self, theme_id: str) -> Theme:
        """Get theme by ID"""
        return self._themes.get(theme_id, self._themes["professional"])
    
    def list_themes(self) -> List[Theme]:
        """List all available themes"""
        return list(self._themes.values())
    
    def get_variant_for_slide_type(self, theme_id: str, slide_type: str, variant_id: Optional[str] = None) -> BackgroundVariant:
        """Get background variant for slide type"""
        theme = self.get_theme(theme_id)
        variants = theme.background_variants.get(slide_type, theme.background_variants.get("BULLET", []))
        
        if variant_id:
            for variant in variants:
                if variant.variant_id == variant_id:
                    return variant
        
        # Return first variant if not specified
        return variants[0] if variants else BackgroundVariant(
            variant_id="default",
            type="solid",
            css="background: #ffffff;",
            tone_tags=[]
        )


# Singleton instance
theme_registry = ThemeRegistry()
