"""Content Quality Verifier - Verifies content quality"""
import logging
from typing import List, Dict, Any
from app.services.slide_studio.ir.schema import SlideIR

logger = logging.getLogger(__name__)


class ContentQualityVerifier:
    """Verifies content quality metrics"""
    
    def verify_content_quality(self, slide_ir: SlideIR) -> Dict[str, Any]:
        """
        Verify content quality and return metrics.
        
        Returns:
            Dict with:
            - clarity_score: float (0-100) - Message clarity
            - structure_score: float (0-100) - Logical flow
            - redundancy_score: float (0-100) - Duplicate content
            - specificity_score: float (0-100) - Concrete examples/data
            - issues: List[Dict] - Content quality issues
        """
        issues: List[Dict[str, Any]] = []
        
        # Clarity check
        clarity_score = self._check_clarity(slide_ir, issues)
        
        # Structure check
        structure_score = self._check_structure(slide_ir, issues)
        
        # Redundancy check
        redundancy_score = self._check_redundancy(slide_ir, issues)
        
        # Specificity check
        specificity_score = self._check_specificity(slide_ir, issues)
        
        return {
            "clarity_score": clarity_score,
            "structure_score": structure_score,
            "redundancy_score": redundancy_score,
            "specificity_score": specificity_score,
            "issues": issues
        }
    
    def _check_clarity(self, slide_ir: SlideIR, issues: List[Dict[str, Any]]) -> float:
        """Check message clarity"""
        score = 100.0
        
        # Check if title is clear
        if not slide_ir.title or len(slide_ir.title.strip()) < 3:
            issues.append({
                "type": "clarity",
                "severity": "error",
                "message": "Slide title is too short or empty"
            })
            score -= 20.0
        
        # Check if content is present
        has_content = False
        for slot in slide_ir.slots.values():
            if slot.slot_type in ["text", "bullet"]:
                if slot.slot_type == "text" and hasattr(slot, 'content') and slot.content:
                    has_content = True
                    break
                elif slot.slot_type == "bullet" and hasattr(slot, 'items') and slot.items:
                    has_content = True
                    break
        
        if not has_content:
            issues.append({
                "type": "clarity",
                "severity": "error",
                "message": "Slide has no content"
            })
            score -= 30.0
        
        return max(0.0, score)
    
    def _check_structure(self, slide_ir: SlideIR, issues: List[Dict[str, Any]]) -> float:
        """Check logical structure"""
        score = 100.0
        
        # Check if title and content are related
        # (Basic check - can be enhanced)
        
        return score
    
    def _check_redundancy(self, slide_ir: SlideIR, issues: List[Dict[str, Any]]) -> float:
        """Check for redundant content"""
        score = 100.0
        
        # Collect all text content
        all_text = []
        for slot in slide_ir.slots.values():
            if slot.slot_type == "text" and hasattr(slot, 'content'):
                all_text.append(slot.content.lower())
            elif slot.slot_type == "bullet" and hasattr(slot, 'items'):
                all_text.extend([item.lower() for item in slot.items])
        
        # Check for duplicate sentences/phrases
        seen = set()
        duplicates = 0
        for text in all_text:
            words = text.split()[:5]  # First 5 words as key
            key = ' '.join(words)
            if key in seen:
                duplicates += 1
            seen.add(key)
        
        if duplicates > 0:
            issues.append({
                "type": "redundancy",
                "severity": "warning",
                "message": f"Found {duplicates} potentially redundant content items"
            })
            score -= duplicates * 5.0
        
        return max(0.0, score)
    
    def _check_specificity(self, slide_ir: SlideIR, issues: List[Dict[str, Any]]) -> float:
        """Check for concrete examples/data"""
        score = 100.0
        
        # Check for numbers/data
        has_numbers = False
        for slot in slide_ir.slots.values():
            if slot.slot_type == "text" and hasattr(slot, 'content'):
                if any(char.isdigit() for char in slot.content):
                    has_numbers = True
                    break
            elif slot.slot_type == "bullet" and hasattr(slot, 'items'):
                if any(any(char.isdigit() for char in item) for item in slot.items):
                    has_numbers = True
                    break
        
        if not has_numbers and slide_ir.slide_type.value in ["CHART", "TABLE", "BULLET"]:
            issues.append({
                "type": "specificity",
                "severity": "warning",
                "message": "Slide could benefit from concrete data/numbers"
            })
            score -= 10.0
        
        return max(0.0, score)


# Singleton instance
content_quality_verifier = ContentQualityVerifier()
