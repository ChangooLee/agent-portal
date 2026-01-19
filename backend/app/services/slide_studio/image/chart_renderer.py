"""Chart Renderer Provider - Renders charts as images"""
import logging
from typing import Optional, Dict, Any
import base64
from io import BytesIO
from app.services.slide_studio.ir.schema import ImageSlot
from app.services.slide_studio.image.provider import ImageProvider

logger = logging.getLogger(__name__)


class ChartRendererProvider(ImageProvider):
    """Renders charts as images"""
    
    async def get_image(
        self,
        slot: ImageSlot,
        context: Dict[str, Any]
    ) -> Optional[str]:
        """Render chart as image"""
        # For Step 5, return placeholder
        # In production, this would use matplotlib/plotly to render actual charts
        try:
            from PIL import Image, ImageDraw
            width = int(slot.bbox.w) if slot.bbox else 800
            height = int(slot.bbox.h) if slot.bbox else 600
            
            img = Image.new('RGB', (width, height), color='white')
            draw = ImageDraw.Draw(img)
            
            # Draw simple chart placeholder
            draw.rectangle([50, 50, width-50, height-50], outline='#6366f1', width=2)
            draw.text((width//2 - 50, height//2), "Chart Placeholder", fill='#9ca3af')
            
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            return f"data:image/png;base64,{img_data}"
            
        except Exception as e:
            logger.error(f"Chart renderer error: {e}")
            return None
    
    def is_available(self) -> bool:
        """Available if PIL is installed"""
        try:
            from PIL import Image
            return True
        except ImportError:
            return False
