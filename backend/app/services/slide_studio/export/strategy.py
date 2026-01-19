"""Export Strategy - Determines native vs image for slots"""
from app.services.slide_studio.ir.schema import SlotUnion, TableSlot, ChartSlot


class ExportStrategy:
    """Determines export strategy for slots"""
    
    @staticmethod
    def should_export_as_image(slot: SlotUnion) -> bool:
        """
        Determine if slot should be exported as image.
        
        Args:
            slot: Slot to check
            
        Returns:
            True if should export as image
        """
        # Chart slots are always images
        if slot.slot_type == "chart":
            return True
        
        # Complex tables are images
        if slot.slot_type == "table":
            table_slot = slot
            if isinstance(table_slot, TableSlot):
                # Complex if more than 5 columns or 10 rows
                if len(table_slot.headers) > 5 or len(table_slot.rows) > 10:
                    return True
        
        # Use slot's export_strategy
        return slot.export_strategy.value == "IMAGE"
