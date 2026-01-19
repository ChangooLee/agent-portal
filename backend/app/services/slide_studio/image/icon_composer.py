"""Icon Composer Provider - Icon + Background + Text"""
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


class IconComposerProvider(ImageProvider):
    """Composes icon + background + text into image"""
    
    def __init__(self):
        self.icon_library_path = Path(slide_studio_config.ASSET_LIBRARY_PATH) / "icons"
    
    async def get_image(
        self,
        slot: ImageSlot,
        context: Dict[str, Any]
    ) -> Optional[str]:
        """Compose icon image"""
        try:
            # Get dimensions
            width = int(slot.bbox.w) if slot.bbox else 400
            height = int(slot.bbox.h) if slot.bbox else 300
            
            # Create image with gradient background
            img = Image.new('RGB', (width, height), color='#6366f1')
            draw = ImageDraw.Draw(img)
            
            # Draw gradient (simple version)
            for i in range(height):
                ratio = i / height
                r = int(99 + (156 - 99) * ratio)  # Purple gradient
                g = int(102 + (182 - 102) * ratio)
                b = int(241 + (255 - 241) * ratio)
                draw.rectangle([(0, i), (width, i+1)], fill=(r, g, b))
            
            # Draw icon placeholder (circle)
            icon_size = min(width, height) // 3
            icon_x = (width - icon_size) // 2
            icon_y = (height - icon_size) // 2 - 20
            draw.ellipse(
                [(icon_x, icon_y), (icon_x + icon_size, icon_y + icon_size)],
                fill='white',
                outline='#8b5cf6',
                width=3
            )
            
            # Draw text
            text = slot.alt_text or context.get('keywords', ['Icon'])[0] if context.get('keywords') else "Icon"
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
            except:
                font = ImageFont.load_default()
            
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_x = (width - text_width) // 2
            text_y = icon_y + icon_size + 20
            
            draw.text((text_x, text_y), text, fill='white', font=font)
            
            # Convert to data URI
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            return f"data:image/png;base64,{img_data}"
            
        except Exception as e:
            logger.error(f"Icon composer error: {e}")
            return None
    
    def is_available(self) -> bool:
        """Available if PIL is installed"""
        try:
            from PIL import Image
            return True
        except ImportError:
            return False
