"""Content Writer - Improves slide content quality"""
import logging
from typing import Optional
from app.services.slide_studio.ir.schema import SlideIR

logger = logging.getLogger(__name__)


class ContentWriter:
    """Improves slide content quality through rewriting"""
    
    async def rewrite_for_slide(self, slide_ir: SlideIR, trace_id: Optional[str] = None) -> SlideIR:
        """
        Rewrite slide content to improve quality.
        
        - Refines bullet points into slide-appropriate sentences
        - Removes redundancy
        - Unifies tone
        - Improves structure
        
        Args:
            slide_ir: Original slide IR
            
        Returns:
            Improved slide IR
        """
        try:
            # For now, return as-is (placeholder)
            # TODO: Implement LLM-based rewriting in future iteration
            # This would call LLM to refine content while maintaining structure
            
            # Basic improvements (non-LLM)
            from app.services.slide_studio.ir.schema import BulletSlot
            
            improved_slots = {}
            for slot_id, slot in slide_ir.slots.items():
                if isinstance(slot, BulletSlot):
                    # Remove empty items
                    if hasattr(slot, 'items') and slot.items:
                        slot.items = [item for item in slot.items if item.strip()]
                
                improved_slots[slot_id] = slot
            
            improved_slide = slide_ir.model_copy()
            improved_slide.slots = improved_slots
            
            return improved_slide
            
        except Exception as e:
            logger.error(f"Content rewriting failed: {e}")
            return slide_ir


# Singleton instance
content_writer = ContentWriter()
