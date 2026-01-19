"""Template Selector - Selects appropriate template for slide"""
import logging
from typing import Optional
from app.services.slide_studio.template.library import template_library
from app.services.slide_studio.template.schema import LayoutTemplate
from app.services.slide_studio.ir.schema import SlideType, SlidePlan

logger = logging.getLogger(__name__)


class TemplateSelector:
    """Selects layout template for slide"""
    
    def __init__(self):
        self.library = template_library
    
    def select_template(
        self,
        slide_type: SlideType,
        slide_ir: "SlideIR",
        preferred_template_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> LayoutTemplate:
        """
        Select template for slide.
        
        Args:
            slide_type: Slide type
            slide_ir: Slide IR
            preferred_template_id: Optional preferred template ID
            trace_id: Parent trace ID for monitoring
            
        Returns:
            Selected LayoutTemplate
        """
        templates = self.library.get_templates_for_slide_type(slide_type)
        
        if not templates:
            logger.warning(f"No templates found for {slide_type.value}, using default")
            return self.library.get_template("default", slide_type)
        
        # If preferred template ID is provided, try to use it
        if preferred_template_id:
            for template in templates:
                if template.template_id == preferred_template_id:
                    return template
        
        # Heuristic selection based on slide goal
        # For now, return first template (can be enhanced with LLM-based selection)
        return templates[0]


# Singleton instance
template_selector = TemplateSelector()
