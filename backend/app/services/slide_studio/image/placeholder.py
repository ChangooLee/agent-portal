"""Placeholder Image Provider"""
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import base64
from io import BytesIO
from app.services.slide_studio.ir.schema import ImageSlot
from app.services.slide_studio.image.provider import ImageProvider
from app.services.slide_studio.config import slide_studio_config

logger = logging.getLogger(__name__)


class PlaceholderProvider(ImageProvider):
    """Provider for placeholder images"""
    
    def __init__(self):
        self.default_width = 800
        self.default_height = 600
    
    async def get_image(
        self,
        slot: ImageSlot,
        context: Dict[str, Any]
    ) -> Optional[str]:
        """Generate placeholder image"""
        try:
            # Get dimensions from bbox if available
            width = int(slot.bbox.w) if slot.bbox else self.default_width
            height = int(slot.bbox.h) if slot.bbox else self.default_height
            
            # Create placeholder image
            img = Image.new('RGB', (width, height), color='#f3f4f6')
            draw = ImageDraw.Draw(img)
            
            # Draw placeholder text
            text = slot.alt_text or "Image Placeholder"
            try:
                # Try to use default font
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
            except:
                font = ImageFont.load_default()
            
            # Center text
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (width - text_width) // 2
            y = (height - text_height) // 2
            
            draw.text((x, y), text, fill='#9ca3af', font=font)
            
            # Convert to data URI
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            return f"data:image/png;base64,{img_data}"
            
        except Exception as e:
            logger.error(f"Placeholder generation error: {e}")
            return None
    
    def is_available(self) -> bool:
        """Always available (uses PIL)"""
        try:
            from PIL import Image
            return True
        except ImportError:
            return False
