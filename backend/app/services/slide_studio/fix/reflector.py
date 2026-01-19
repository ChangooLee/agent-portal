"""Reflector - Analyzes issues and generates fixes"""
import logging
from typing import List, Dict, Any, Optional
from app.services.slide_studio.ir.schema import SlideIR

logger = logging.getLogger(__name__)


class Reflector:
    """Reflects on issues and generates fix suggestions"""
    
    async def reflect(
        self,
        slide_ir: SlideIR,
        issues: List[Dict[str, Any]],
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze issues and generate fix suggestions.
        
        Uses LLM for sophisticated analysis when possible, falls back to heuristic.
        
        Args:
            slide_ir: Slide IR
            issues: List of issues
            
        Returns:
            Fix suggestions dict with action type that triggers LLM regeneration
        """
        suggestions = {
            "actions": [],
            "reasoning": ""
        }
        
        # Analyze issues
        error_issues = [i for i in issues if i.get("severity") == "error"]
        overflow_issues = [i for i in issues if i.get("type") == "overflow"]
        overlap_issues = [i for i in issues if i.get("type") == "overlap"]
        font_issues = [i for i in issues if i.get("type") == "font_too_small"]
        
        # If there are error issues (overflow, overlap), use LLM regeneration
        if error_issues:
            # Determine primary issue type
            if overflow_issues:
                suggestions["actions"].append({
                    "type": "regenerate",  # Triggers LLM regeneration
                    "target": overflow_issues[0].get("slot_id"),
                    "reason": "Text overflows container - need to improve content structure"
                })
                suggestions["reasoning"] = f"Text overflow detected in {overflow_issues[0].get('slot_id', 'slot')}. " \
                                         f"Need to regenerate slide content with better structure and concise text."
            elif overlap_issues:
                suggestions["actions"].append({
                    "type": "regenerate",  # Triggers LLM regeneration
                    "target": overlap_issues[0].get("slot_id"),
                    "reason": "Slots overlap - need to improve layout and content"
                })
                suggestions["reasoning"] = f"Overlap detected. Need to regenerate with better layout planning."
            else:
                # Other error issues - use regenerate
                suggestions["actions"].append({
                    "type": "regenerate",
                    "target": None,
                    "reason": "Quality issues detected - need to improve overall slide"
                })
                suggestions["reasoning"] = f"Quality issues detected: {len(error_issues)} errors. " \
                                         f"Need to regenerate slide with improvements."
        elif font_issues:
            # Font issues can be fixed with auto_fix
            suggestions["actions"].append({
                "type": "increase_font",
                "target": font_issues[0].get("slot_id"),
                "reason": "Font too small"
            })
            suggestions["reasoning"] = "Font size issue detected."
        else:
            # No critical issues, but score might be low - try to improve
            suggestions["actions"].append({
                "type": "regenerate",
                "target": None,
                "reason": "Improve overall slide quality"
            })
            suggestions["reasoning"] = "Improving slide quality and content structure."
        
        if not suggestions["reasoning"]:
            suggestions["reasoning"] = "No critical issues found."
        
        return suggestions


# Singleton instance
reflector = Reflector()
