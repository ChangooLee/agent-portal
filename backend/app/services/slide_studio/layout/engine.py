"""Layout Engine - Calculates coordinates and grid layout"""
from typing import Dict, List, Optional
from app.services.slide_studio.ir.schema import SlideIR, BBox, SlotUnion
from app.services.slide_studio.layout.rules import get_layout_rules, calculate_bbox
from app.services.slide_studio.layout.tokens import default_tokens
from app.services.slide_studio.config import slide_studio_config
from app.services.slide_studio.template.selector import template_selector
from app.services.slide_studio.template.schema import LayoutTemplate


class LayoutEngine:
    """Calculates layout coordinates for slides"""
    
    def __init__(self):
        self.slide_width = slide_studio_config.SLIDE_WIDTH
        self.slide_height = slide_studio_config.SLIDE_HEIGHT
    
    def layout_slide(
        self,
        slide_ir: SlideIR,
        template: Optional[LayoutTemplate] = None,
        theme_id: Optional[str] = None,
        theme_variant_map: Optional[Dict[str, str]] = None
    ) -> SlideIR:
        """
        Calculate layout for a slide using template.
        
        Args:
            slide_ir: Slide IR without bbox
            template: Optional template (if None, will be selected)
            theme_id: Optional theme ID for styling
            theme_variant_map: Optional theme variant mapping
            
        Returns:
            Slide IR with bbox calculated
        """
        # Select template if not provided
        if not template:
            from app.services.slide_studio.ir.schema import SlidePlan
            # Create a dummy slide plan for template selection
            slide_plan = SlidePlan(
                slide_id=slide_ir.slide_id,
                title=slide_ir.title,
                slide_type=slide_ir.slide_type
            )
            template = template_selector.select_template(slide_plan)
        
        # Use template-based layout
        updated_slots: Dict[str, SlotUnion] = {}
        
        for slot_id, slot in slide_ir.slots.items():
            # Check if template has layout for this slot
            if slot_id in template.slot_layouts:
                slot_layout = template.slot_layouts[slot_id]
                bbox = self._calculate_bbox_from_template(
                    slot_layout,
                    template.grid,
                    self.slide_width,
                    self.slide_height
                )
                
                # Update slot with bbox
                if hasattr(slot, 'bbox'):
                    slot.bbox = bbox
            else:
                # Fallback to default layout rules
                rules = get_layout_rules(slide_ir.slide_type)
                regions = rules.get("regions", [])
                if regions:
                    region = regions[0]  # Use first region
                    bbox = calculate_bbox(region, self.slide_width, self.slide_height)
                    if hasattr(slot, 'bbox'):
                        slot.bbox = bbox
            
            updated_slots[slot_id] = slot
        
        # Create updated slide IR
        updated_slide = slide_ir.model_copy()
        updated_slide.slots = updated_slots
        
        return updated_slide
    
    def _calculate_bbox_from_template(
        self,
        slot_layout,
        grid_config,
        slide_width: int,
        slide_height: int
    ) -> BBox:
        """Calculate bbox from template slot layout"""
        # Calculate column width
        available_width = slide_width - (grid_config.margin * 2)
        column_width = (available_width - (grid_config.gutter * (grid_config.columns - 1))) / grid_config.columns
        
        # Calculate row height (approximate)
        available_height = slide_height - (grid_config.margin * 2)
        row_height = available_height / 12  # Assume 12 rows
        
        # Calculate position
        x = grid_config.margin + (slot_layout.grid_column_start - 1) * (column_width + grid_config.gutter)
        y = grid_config.margin + (slot_layout.grid_row_start - 1) * (row_height + grid_config.gutter)
        
        # Calculate size
        w = slot_layout.grid_column_span * column_width + (slot_layout.grid_column_span - 1) * grid_config.gutter
        h = slot_layout.grid_row_span * row_height + (slot_layout.grid_row_span - 1) * grid_config.gutter
        
        # Apply min/max constraints
        if slot_layout.min_width:
            w = max(w, slot_layout.min_width)
        if slot_layout.min_height:
            h = max(h, slot_layout.min_height)
        if slot_layout.max_width:
            w = min(w, slot_layout.max_width)
        if slot_layout.max_height:
            h = min(h, slot_layout.max_height)
        
        return BBox(x=int(x), y=int(y), w=int(w), h=int(h))
    
    def snap_to_grid(self, bbox: BBox) -> BBox:
        """
        Snap bbox to grid.
        
        Args:
            bbox: Original bbox
            
        Returns:
            Snapped bbox
        """
        grid_size = default_tokens.spacing["grid"]
        
        return BBox(
            x=round(bbox.x / grid_size) * grid_size,
            y=round(bbox.y / grid_size) * grid_size,
            w=round(bbox.w / grid_size) * grid_size,
            h=round(bbox.h / grid_size) * grid_size
        )


# Singleton instance
layout_engine = LayoutEngine()
