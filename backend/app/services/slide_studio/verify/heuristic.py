"""Heuristic Verifier - Basic quality checks"""
import logging
from typing import List, Dict, Any
from app.services.slide_studio.ir.schema import SlideIR, BBox, TextSlot, BulletSlot
from app.services.slide_studio.layout.tokens import default_tokens
from app.services.slide_studio.config import slide_studio_config

logger = logging.getLogger(__name__)


class HeuristicVerifier:
    """Heuristic-based quality verification"""
    
    def __init__(self):
        self.min_font_size = slide_studio_config.MIN_FONT_SIZE
        self.slide_width = slide_studio_config.SLIDE_WIDTH
        self.slide_height = slide_studio_config.SLIDE_HEIGHT
    
    def verify_slide(self, slide_ir: SlideIR, use_playwright: bool = False) -> List[Dict[str, Any]]:
        """
        Verify slide quality using heuristics.
        
        Args:
            slide_ir: Slide IR with layout
            
        Returns:
            List of issues
        """
        issues = []
        
        for slot_id, slot in slide_ir.slots.items():
            if not slot.bbox:
                continue
            
            # Check overflow
            overflow_issues = self._check_overflow(slot, slot.bbox)
            issues.extend(overflow_issues)
            
            # Check font size
            font_issues = self._check_font_size(slot)
            issues.extend(font_issues)
            
            # Check margin violations
            margin_issues = self._check_margins(slot, slot.bbox, slide_ir.slide_type)
            issues.extend(margin_issues)
        
        # Check overlaps
        overlap_issues = self._check_overlaps(slide_ir)
        issues.extend(overlap_issues)
        
        # Playwright verification (if requested and available)
        if use_playwright:
            from app.services.slide_studio.verify.playwright import playwright_verifier
            if playwright_verifier.available:
                playwright_issues = playwright_verifier.verify_slide_with_playwright(slide_ir)
                issues.extend(playwright_issues)
        
        return issues
    
    def _check_overflow(self, slot, bbox: BBox) -> List[Dict[str, Any]]:
        """Check if content overflows bbox"""
        issues = []
        
        if slot.slot_type == "text":
            # Estimate text height
            estimated_height = self._estimate_text_height(slot.content, bbox.w)
            if estimated_height > bbox.h:
                issues.append({
                    "severity": "error",
                    "slot": slot.slot_type,
                    "type": "overflow",
                    "message": f"Text overflows container (estimated: {estimated_height:.0f}px, available: {bbox.h:.0f}px)",
                    "slot_id": getattr(slot, 'slot_id', None)
                })
        
        elif slot.slot_type == "bullet":
            # Estimate bullet list height
            estimated_height = self._estimate_bullet_height(slot.items, bbox.w)
            if estimated_height > bbox.h:
                issues.append({
                    "severity": "error",
                    "slot": slot.slot_type,
                    "type": "overflow",
                    "message": f"Bullet list overflows container (estimated: {estimated_height:.0f}px, available: {bbox.h:.0f}px)",
                    "slot_id": getattr(slot, 'slot_id', None)
                })
        
        return issues
    
    def _check_font_size(self, slot) -> List[Dict[str, Any]]:
        """Check if font size is too small"""
        issues = []
        
        if hasattr(slot, 'style') and slot.style and slot.style.font_size:
            if slot.style.font_size < self.min_font_size:
                issues.append({
                    "severity": "warning",
                    "slot": slot.slot_type,
                    "type": "font_too_small",
                    "message": f"Font size ({slot.style.font_size}px) is below minimum ({self.min_font_size}px)",
                    "slot_id": getattr(slot, 'slot_id', None)
                })
        
        return issues
    
    def _check_margins(self, slot, bbox: BBox, slide_type) -> List[Dict[str, Any]]:
        """Check safe margin violations"""
        issues = []
        
        # Get safe margin for slide type
        safe_margin_pct = default_tokens.safe_margins.get(
            slide_type.value.lower(),
            default_tokens.safe_margins["default"]
        )
        
        margin_x = self.slide_width * safe_margin_pct
        margin_y = self.slide_height * safe_margin_pct
        
        if bbox.x < margin_x:
            issues.append({
                "severity": "warning",
                "slot": slot.slot_type,
                "type": "margin_violation",
                "message": f"Left margin violation (x: {bbox.x:.0f}px, safe: {margin_x:.0f}px)",
                "slot_id": getattr(slot, 'slot_id', None)
            })
        
        if bbox.y < margin_y:
            issues.append({
                "severity": "warning",
                "slot": slot.slot_type,
                "type": "margin_violation",
                "message": f"Top margin violation (y: {bbox.y:.0f}px, safe: {margin_y:.0f}px)",
                "slot_id": getattr(slot, 'slot_id', None)
            })
        
        if bbox.x + bbox.w > self.slide_width - margin_x:
            issues.append({
                "severity": "warning",
                "slot": slot.slot_type,
                "type": "margin_violation",
                "message": f"Right margin violation",
                "slot_id": getattr(slot, 'slot_id', None)
            })
        
        if bbox.y + bbox.h > self.slide_height - margin_y:
            issues.append({
                "severity": "warning",
                "slot": slot.slot_type,
                "type": "margin_violation",
                "message": f"Bottom margin violation",
                "slot_id": getattr(slot, 'slot_id', None)
            })
        
        return issues
    
    def _check_overlaps(self, slide_ir: SlideIR) -> List[Dict[str, Any]]:
        """Check if slots overlap"""
        issues = []
        slots_with_bbox = [
            (slot_id, slot, slot.bbox)
            for slot_id, slot in slide_ir.slots.items()
            if slot.bbox
        ]
        
        for i, (id1, slot1, bbox1) in enumerate(slots_with_bbox):
            for j, (id2, slot2, bbox2) in enumerate(slots_with_bbox[i+1:], i+1):
                if self._bboxes_overlap(bbox1, bbox2):
                    issues.append({
                        "severity": "error",
                        "slot": slot1.slot_type,
                        "type": "overlap",
                        "message": f"Slot overlaps with {id2}",
                        "slot_id": id1
                    })
        
        return issues
    
    def _bboxes_overlap(self, bbox1: BBox, bbox2: BBox) -> bool:
        """Check if two bboxes overlap"""
        return not (
            bbox1.x + bbox1.w <= bbox2.x or
            bbox2.x + bbox2.w <= bbox1.x or
            bbox1.y + bbox1.h <= bbox2.y or
            bbox2.y + bbox2.h <= bbox1.y
        )
    
    def _estimate_text_height(self, text: str, width: float) -> float:
        """Estimate text height (Korean-aware)"""
        # Average character width (Korean-aware)
        avg_char_width = 20.0  # pixels (approximate for Korean)
        chars_per_line = max(1, int(width / avg_char_width))
        num_lines = max(1, (len(text) + chars_per_line - 1) // chars_per_line)
        
        # Line height with Korean correction
        line_height = 30.0  # pixels (approximate)
        return num_lines * line_height
    
    def _estimate_bullet_height(self, items: List[str], width: float) -> float:
        """Estimate bullet list height"""
        total_height = 0.0
        for item in items:
            item_height = self._estimate_text_height(item, width - 40.0)  # Account for bullet indent
            total_height += item_height + 8.0  # Item spacing
        return total_height


# Singleton instance
heuristic_verifier = HeuristicVerifier()
