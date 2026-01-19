"""Auto Fix - Applies fixes to slides"""
import logging
from typing import List, Dict, Any
from app.services.slide_studio.ir.schema import SlideIR, TextSlot, BulletSlot, BBox
from app.services.slide_studio.config import slide_studio_config

logger = logging.getLogger(__name__)


class AutoFix:
    """Applies automatic fixes to slides"""
    
    def apply_fix(
        self,
        slide_ir: SlideIR,
        fix_type: str,
        target_slot_id: str = None
    ) -> SlideIR:
        """
        Apply a fix to slide.
        
        Args:
            slide_ir: Slide IR
            fix_type: Type of fix (shorten_text, split_slide, simplify_layout, shrink_to_fit)
            target_slot_id: Target slot ID (optional)
            
        Returns:
            Updated SlideIR
        """
        if fix_type == "shorten_text":
            return self._shorten_text(slide_ir, target_slot_id)
        elif fix_type == "split_slide":
            return self._split_slide(slide_ir)
        elif fix_type == "simplify_layout":
            return self._simplify_layout(slide_ir)
        elif fix_type == "shrink_to_fit":
            return self._shrink_to_fit(slide_ir, target_slot_id)
        else:
            logger.warning(f"Unknown fix type: {fix_type}")
            return slide_ir
    
    def _shorten_text(self, slide_ir: SlideIR, slot_id: str = None) -> SlideIR:
        """Shorten text in slot"""
        updated_slots = {}
        for sid, slot in slide_ir.slots.items():
            if slot_id and sid != slot_id:
                updated_slots[sid] = slot
                continue
            
            if slot.slot_type == "text":
                # Truncate to 80% of original
                new_content = slot.content[:int(len(slot.content) * 0.8)] + "..."
                updated_slots[sid] = TextSlot(
                    slot_type="text",
                    content=new_content,
                    bbox=slot.bbox,
                    style=slot.style,
                    export_strategy=slot.export_strategy
                )
            elif slot.slot_type == "bullet":
                # Reduce items to 80%
                new_items = slot.items[:max(1, int(len(slot.items) * 0.8))]
                updated_slots[sid] = BulletSlot(
                    slot_type="bullet",
                    items=new_items,
                    bbox=slot.bbox,
                    style=slot.style,
                    export_strategy=slot.export_strategy
                )
            else:
                updated_slots[sid] = slot
        
        updated_slide = slide_ir.model_copy()
        updated_slide.slots = updated_slots
        return updated_slide
    
    def _split_slide(self, slide_ir: SlideIR) -> SlideIR:
        """Split slide (not implemented in Step 3)"""
        # TODO: Implement in Step 3+
        logger.warning("Split slide not yet implemented")
        return slide_ir
    
    def _simplify_layout(self, slide_ir: SlideIR) -> SlideIR:
        """Simplify layout (e.g., 2-column -> 1-column)"""
        # TODO: Implement in Step 3+
        logger.warning("Simplify layout not yet implemented")
        return slide_ir
    
    def _shrink_to_fit(self, slide_ir: SlideIR, slot_id: str = None) -> SlideIR:
        """Shrink font to fit (with min font size limit)"""
        updated_slots = {}
        for sid, slot in slide_ir.slots.items():
            if slot_id and sid != slot_id:
                updated_slots[sid] = slot
                continue
            
            if hasattr(slot, 'style') and slot.style:
                # Reduce font size but not below minimum
                new_font_size = max(
                    slide_studio_config.MIN_FONT_SIZE,
                    int((slot.style.font_size or 18) * 0.9)
                )
                updated_style = slot.style.model_copy()
                updated_style.font_size = new_font_size
                updated_slot = slot.model_copy()
                updated_slot.style = updated_style
                updated_slots[sid] = updated_slot
            else:
                updated_slots[sid] = slot
        
        updated_slide = slide_ir.model_copy()
        updated_slide.slots = updated_slots
        return updated_slide


# Singleton instance
auto_fix = AutoFix()
