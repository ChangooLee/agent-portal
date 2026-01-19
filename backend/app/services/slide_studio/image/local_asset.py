"""Local Asset Library Provider"""
import logging
from typing import Optional, Dict, Any
from app.services.slide_studio.ir.schema import ImageSlot
from app.services.slide_studio.image.provider import ImageProvider
from app.services.slide_studio.assets.manager import assets_manager

logger = logging.getLogger(__name__)


class LocalAssetLibraryProvider(ImageProvider):
    """Provider for local asset library"""
    
    async def get_image(
        self,
        slot: ImageSlot,
        context: Dict[str, Any]
    ) -> Optional[str]:
        """Get image from local asset library"""
        # Search assets by keywords from context
        keywords = context.get('keywords', [])
        if not keywords and slot.alt_text:
            keywords = [slot.alt_text]
        
        assets = assets_manager.search_assets(
            asset_type='photo',  # or 'illustration'
            keywords=keywords
        )
        
        if assets:
            asset_path = assets_manager.get_asset_path(assets[0]['id'])
            if asset_path:
                return f"/assets/{asset_path.name}"
        
        return None
    
    def is_available(self) -> bool:
        """Available if asset library exists"""
        return assets_manager.library_path.exists()
