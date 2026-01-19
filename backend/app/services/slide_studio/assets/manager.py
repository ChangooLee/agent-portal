"""Assets Manager - Manages local asset library"""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.services.slide_studio.config import slide_studio_config

logger = logging.getLogger(__name__)


class AssetsManager:
    """Manages local asset library (icons, images, fonts)"""
    
    def __init__(self):
        self.library_path = Path(slide_studio_config.ASSET_LIBRARY_PATH)
        self.library_path.mkdir(parents=True, exist_ok=True)
    
    def search_assets(
        self,
        asset_type: str = None,
        tags: List[str] = None,
        keywords: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search assets in library.
        
        Args:
            asset_type: Type filter (icon, photo, illustration, bg)
            tags: Tag filters
            keywords: Keyword search
            
        Returns:
            List of asset metadata
        """
        assets = []
        
        # For Step 5, return empty list (library not populated yet)
        # In production, this would scan library_path and match metadata
        
        return assets
    
    def get_asset_path(self, asset_id: str) -> Optional[Path]:
        """Get path to asset by ID"""
        asset_file = self.library_path / asset_id
        return asset_file if asset_file.exists() else None
    
    def list_assets(self, asset_type: str = None) -> List[Dict[str, Any]]:
        """List all assets (optionally filtered by type)"""
        assets = []
        
        if asset_type:
            type_dir = self.library_path / asset_type
            if type_dir.exists():
                for asset_file in type_dir.iterdir():
                    if asset_file.is_file():
                        assets.append({
                            "id": asset_file.name,
                            "type": asset_type,
                            "path": str(asset_file)
                        })
        else:
            # List all types
            for type_dir in self.library_path.iterdir():
                if type_dir.is_dir():
                    for asset_file in type_dir.iterdir():
                        if asset_file.is_file():
                            assets.append({
                                "id": asset_file.name,
                                "type": type_dir.name,
                                "path": str(asset_file)
                            })
        
        return assets


# Singleton instance
assets_manager = AssetsManager()
