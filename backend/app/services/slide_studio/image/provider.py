"""ImageProvider Interface and Chain"""
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from app.services.slide_studio.ir.schema import ImageSlot

logger = logging.getLogger(__name__)


class ImageProvider(ABC):
    """Base class for image providers"""
    
    @abstractmethod
    async def get_image(
        self,
        slot: ImageSlot,
        context: Dict[str, Any]
    ) -> Optional[str]:
        """
        Get image URL or path for slot.
        
        Args:
            slot: ImageSlot
            context: Additional context (slide type, keywords, etc.)
            
        Returns:
            Image URL/path or None if not available
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available"""
        pass


class ImageProviderChain:
    """Chain of image providers with fallback"""
    
    def __init__(self, providers: list[ImageProvider]):
        self.providers = providers
    
    async def get_image(
        self,
        slot: ImageSlot,
        context: Dict[str, Any]
    ) -> Optional[str]:
        """
        Try providers in order until one succeeds.
        
        Args:
            slot: ImageSlot
            context: Additional context
            
        Returns:
            Image URL/path or None if all providers fail
        """
        for provider in self.providers:
            if not provider.is_available():
                continue
            
            try:
                image_url = await provider.get_image(slot, context)
                if image_url:
                    return image_url
            except Exception as e:
                logger.warning(f"ImageProvider {provider.__class__.__name__} failed: {e}")
                continue
        
        return None
