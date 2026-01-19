"""Flux Client Provider (Optional)"""
import logging
from typing import Optional, Dict, Any
from app.services.slide_studio.ir.schema import ImageSlot
from app.services.slide_studio.image.provider import ImageProvider

logger = logging.getLogger(__name__)


class FluxProvider(ImageProvider):
    """FLUX image generation provider (optional)"""
    
    def __init__(self):
        self.flux_api_url = None  # Set from config if available
        self.available = False
    
    async def get_image(
        self,
        slot: ImageSlot,
        context: Dict[str, Any]
    ) -> Optional[str]:
        """Generate image using FLUX"""
        # For Step 5, return None (not implemented)
        # In production, this would call FLUX API
        logger.debug("FLUX provider not implemented")
        return None
    
    def is_available(self) -> bool:
        """Check if FLUX is available"""
        return self.available and self.flux_api_url is not None
