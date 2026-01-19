"""Layout rules for different slide types"""
from typing import Dict, List, Tuple
from app.services.slide_studio.ir.schema import SlideType, BBox
from app.services.slide_studio.layout.tokens import default_tokens


def get_layout_rules(slide_type: SlideType) -> Dict[str, any]:
    """
    Get layout rules for a slide type.
    
    Returns:
        Dictionary with layout configuration
    """
    rules = {
        SlideType.TITLE: {
            "regions": [
                {"id": "title", "x": 0.1, "y": 0.3, "w": 0.8, "h": 0.2}
            ],
            "safe_margin": default_tokens.safe_margins["title"]
        },
        SlideType.AGENDA: {
            "regions": [
                {"id": "title", "x": 0.1, "y": 0.1, "w": 0.8, "h": 0.15},
                {"id": "content", "x": 0.1, "y": 0.3, "w": 0.8, "h": 0.6}
            ],
            "safe_margin": default_tokens.safe_margins["bullet"]
        },
        SlideType.TWO_COLUMN: {
            "regions": [
                {"id": "title", "x": 0.1, "y": 0.1, "w": 0.8, "h": 0.15},
                {"id": "left", "x": 0.1, "y": 0.3, "w": 0.35, "h": 0.6},
                {"id": "right", "x": 0.55, "y": 0.3, "w": 0.35, "h": 0.6}
            ],
            "safe_margin": default_tokens.safe_margins["default"]
        },
        SlideType.BULLET: {
            "regions": [
                {"id": "title", "x": 0.1, "y": 0.1, "w": 0.8, "h": 0.15},
                {"id": "content", "x": 0.1, "y": 0.3, "w": 0.8, "h": 0.6}
            ],
            "safe_margin": default_tokens.safe_margins["bullet"]
        },
        SlideType.IMAGE: {
            "regions": [
                {"id": "title", "x": 0.1, "y": 0.1, "w": 0.8, "h": 0.15},
                {"id": "image", "x": 0.1, "y": 0.3, "w": 0.8, "h": 0.5},
                {"id": "caption", "x": 0.1, "y": 0.85, "w": 0.8, "h": 0.1}
            ],
            "safe_margin": default_tokens.safe_margins["default"]
        },
        SlideType.CHART: {
            "regions": [
                {"id": "title", "x": 0.1, "y": 0.1, "w": 0.8, "h": 0.15},
                {"id": "chart", "x": 0.1, "y": 0.3, "w": 0.8, "h": 0.6}
            ],
            "safe_margin": default_tokens.safe_margins["default"]
        },
        SlideType.TABLE: {
            "regions": [
                {"id": "title", "x": 0.1, "y": 0.1, "w": 0.8, "h": 0.15},
                {"id": "table", "x": 0.1, "y": 0.3, "w": 0.8, "h": 0.6}
            ],
            "safe_margin": default_tokens.safe_margins["table"]
        },
        SlideType.SECTION: {
            "regions": [
                {"id": "title", "x": 0.1, "y": 0.1, "w": 0.8, "h": 0.2},
                {"id": "content", "x": 0.1, "y": 0.35, "w": 0.8, "h": 0.55}
            ],
            "safe_margin": default_tokens.safe_margins["default"]
        }
    }
    
    return rules.get(slide_type, rules[SlideType.BULLET])


def calculate_bbox(
    region: Dict[str, float],
    slide_width: int,
    slide_height: int
) -> BBox:
    """
    Calculate absolute bbox from relative region.
    
    Args:
        region: Region dict with x, y, w, h (0.0-1.0)
        slide_width: Slide width in pixels
        slide_height: Slide height in pixels
        
    Returns:
        BBox with absolute coordinates
    """
    from app.services.slide_studio.ir.schema import BBox
    
    return BBox(
        x=region["x"] * slide_width,
        y=region["y"] * slide_height,
        w=region["w"] * slide_width,
        h=region["h"] * slide_height
    )
