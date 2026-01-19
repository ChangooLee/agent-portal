"""User Provided Image Provider"""
from typing import Optional, Dict, Any
from app.services.slide_studio.ir.schema import ImageSlot
from app.services.slide_studio.image.provider import ImageProvider


class UserProvidedImageProvider(ImageProvider):
    """Provider for user-uploaded images"""
    
    def __init__(self):
        self.upload_base_path = "/data/slide-studio/uploads"
    
    async def get_image(
        self,
        slot: ImageSlot,
        context: Dict[str, Any]
    ) -> Optional[str]:
        """Get user-provided image"""
        if slot.image_url:
            # Check if it's a user upload
            if slot.image_url.startswith("/uploads/") or slot.image_url.startswith("http"):
                return slot.image_url
        return None
    
    def is_available(self) -> bool:
        """Always available"""
        return True
