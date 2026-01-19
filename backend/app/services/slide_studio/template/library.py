"""Template Library - Predefined layout templates"""
from typing import Dict, List
from app.services.slide_studio.template.schema import (
    LayoutTemplate, GridConfig, SlotLayout, TypographyStyle, SpacingRules, DecorativeElement
)
from app.services.slide_studio.ir.schema import SlideType


class TemplateLibrary:
    """Library of predefined layout templates"""
    
    def __init__(self):
        self._templates: Dict[str, List[LayoutTemplate]] = {}
        self._load_default_templates()
    
    def _load_default_templates(self):
        """Load default templates for each slide type"""
        
        # TITLE templates
        title_templates = [
            LayoutTemplate(
                template_id="title_centered",
                slide_type=SlideType.TITLE,
                name="Centered Title",
                description="Centered title with optional subtitle",
                grid=GridConfig(columns=12, gutter=16, margin=48),
                slot_layouts={
                    "title": SlotLayout(
                        slot_id="title",
                        grid_column_start=2,
                        grid_column_span=8,
                        grid_row_start=4,
                        grid_row_span=2,
                        min_width=600,
                        min_height=100
                    ),
                    "subtitle": SlotLayout(
                        slot_id="subtitle",
                        grid_column_start=2,
                        grid_column_span=8,
                        grid_row_start=6,
                        grid_row_span=1,
                        min_width=600,
                        min_height=50
                    )
                },
                typography_hierarchy={
                    "title": TypographyStyle(font_size=64, font_weight="700", line_height=1.2),
                    "subtitle": TypographyStyle(font_size=28, font_weight="400", line_height=1.4)
                },
                spacing_rules=SpacingRules(slot_gap=24, section_margin=0, content_padding=0)
            ),
            LayoutTemplate(
                template_id="title_left",
                slide_type=SlideType.TITLE,
                name="Left-Aligned Title",
                description="Left-aligned title with subtitle",
                grid=GridConfig(columns=12, gutter=16, margin=48),
                slot_layouts={
                    "title": SlotLayout(
                        slot_id="title",
                        grid_column_start=2,
                        grid_column_span=8,
                        grid_row_start=4,
                        grid_row_span=2,
                        min_width=600,
                        min_height=100
                    ),
                    "subtitle": SlotLayout(
                        slot_id="subtitle",
                        grid_column_start=2,
                        grid_column_span=8,
                        grid_row_start=6,
                        grid_row_span=1,
                        min_width=600,
                        min_height=50
                    )
                },
                typography_hierarchy={
                    "title": TypographyStyle(font_size=56, font_weight="700", line_height=1.2),
                    "subtitle": TypographyStyle(font_size=24, font_weight="400", line_height=1.4)
                },
                spacing_rules=SpacingRules(slot_gap=24, section_margin=0, content_padding=0)
            )
        ]
        
        # BULLET templates
        bullet_templates = [
            LayoutTemplate(
                template_id="bullet_standard",
                slide_type=SlideType.BULLET,
                name="Standard Bullet List",
                description="Standard bullet list with title",
                grid=GridConfig(columns=12, gutter=16, margin=48),
                slot_layouts={
                    "title": SlotLayout(
                        slot_id="title",
                        grid_column_start=2,
                        grid_column_span=8,
                        grid_row_start=1,
                        grid_row_span=1,
                        min_width=600,
                        min_height=60
                    ),
                    "content": SlotLayout(
                        slot_id="content",
                        grid_column_start=2,
                        grid_column_span=8,
                        grid_row_start=2,
                        grid_row_span=6,
                        min_width=600,
                        min_height=400
                    )
                },
                typography_hierarchy={
                    "title": TypographyStyle(font_size=36, font_weight="600", line_height=1.3),
                    "body": TypographyStyle(font_size=20, font_weight="400", line_height=1.6)
                },
                spacing_rules=SpacingRules(slot_gap=24, section_margin=32, content_padding=24)
            ),
            LayoutTemplate(
                template_id="bullet_icon",
                slide_type=SlideType.BULLET,
                name="Icon-Based Bullet List",
                description="Bullet list with icons",
                grid=GridConfig(columns=12, gutter=16, margin=48),
                slot_layouts={
                    "title": SlotLayout(
                        slot_id="title",
                        grid_column_start=2,
                        grid_column_span=8,
                        grid_row_start=1,
                        grid_row_span=1,
                        min_width=600,
                        min_height=60
                    ),
                    "content": SlotLayout(
                        slot_id="content",
                        grid_column_start=2,
                        grid_column_span=8,
                        grid_row_start=2,
                        grid_row_span=6,
                        min_width=600,
                        min_height=400
                    )
                },
                typography_hierarchy={
                    "title": TypographyStyle(font_size=36, font_weight="600", line_height=1.3),
                    "body": TypographyStyle(font_size=20, font_weight="400", line_height=1.6)
                },
                spacing_rules=SpacingRules(slot_gap=24, section_margin=32, content_padding=24)
            )
        ]
        
        # SECTION templates
        section_templates = [
            LayoutTemplate(
                template_id="section_centered",
                slide_type=SlideType.SECTION,
                name="Centered Section",
                description="Centered section divider",
                grid=GridConfig(columns=12, gutter=16, margin=48),
                slot_layouts={
                    "title": SlotLayout(
                        slot_id="title",
                        grid_column_start=2,
                        grid_column_span=8,
                        grid_row_start=4,
                        grid_row_span=2,
                        min_width=600,
                        min_height=100
                    )
                },
                typography_hierarchy={
                    "title": TypographyStyle(font_size=48, font_weight="700", line_height=1.2)
                },
                spacing_rules=SpacingRules(slot_gap=0, section_margin=0, content_padding=0)
            )
        ]
        
        # TWO_COLUMN templates
        two_column_templates = [
            LayoutTemplate(
                template_id="two_column_equal",
                slide_type=SlideType.TWO_COLUMN,
                name="Equal Two Column",
                description="Two equal columns",
                grid=GridConfig(columns=12, gutter=16, margin=48),
                slot_layouts={
                    "title": SlotLayout(
                        slot_id="title",
                        grid_column_start=2,
                        grid_column_span=10,
                        grid_row_start=1,
                        grid_row_span=1,
                        min_width=600,
                        min_height=60
                    ),
                    "left": SlotLayout(
                        slot_id="left",
                        grid_column_start=2,
                        grid_column_span=5,
                        grid_row_start=2,
                        grid_row_span=6,
                        min_width=400,
                        min_height=400
                    ),
                    "right": SlotLayout(
                        slot_id="right",
                        grid_column_start=7,
                        grid_column_span=5,
                        grid_row_start=2,
                        grid_row_span=6,
                        min_width=400,
                        min_height=400
                    )
                },
                typography_hierarchy={
                    "title": TypographyStyle(font_size=36, font_weight="600", line_height=1.3),
                    "body": TypographyStyle(font_size=18, font_weight="400", line_height=1.6)
                },
                spacing_rules=SpacingRules(slot_gap=24, section_margin=32, content_padding=24)
            )
        ]
        
        self._templates[SlideType.TITLE.value] = title_templates
        self._templates[SlideType.BULLET.value] = bullet_templates
        self._templates[SlideType.SECTION.value] = section_templates
        self._templates[SlideType.TWO_COLUMN.value] = two_column_templates
        
        # Default templates for other types
        for slide_type in [SlideType.AGENDA, SlideType.IMAGE, SlideType.CHART, SlideType.TABLE]:
            self._templates[slide_type.value] = [
                LayoutTemplate(
                    template_id=f"{slide_type.value.lower()}_default",
                    slide_type=slide_type,
                    name="Default",
                    description=f"Default template for {slide_type.value}",
                    grid=GridConfig(),
                    slot_layouts={},
                    typography_hierarchy={},
                    spacing_rules=SpacingRules()
                )
            ]
    
    def get_templates_for_slide_type(self, slide_type: SlideType) -> List[LayoutTemplate]:
        """Get templates for a slide type"""
        return self._templates.get(slide_type.value, [])
    
    def get_template(self, template_id: str, slide_type: SlideType) -> LayoutTemplate:
        """Get template by ID"""
        templates = self.get_templates_for_slide_type(slide_type)
        for template in templates:
            if template.template_id == template_id:
                return template
        
        # Return first template as fallback
        if templates:
            return templates[0]
        
        # Return default template
        return LayoutTemplate(
            template_id="default",
            slide_type=slide_type,
            name="Default",
            description="Default template",
            grid=GridConfig(),
            slot_layouts={},
            typography_hierarchy={},
            spacing_rules=SpacingRules()
        )


# Singleton instance
template_library = TemplateLibrary()
