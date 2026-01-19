"""Background Image Registry - Available background images"""
from typing import Dict, List, Optional
from pydantic import BaseModel
from pathlib import Path


class BackgroundImageInfo(BaseModel):
    """Background image information"""
    image_id: str
    name: str
    description: str
    category: str  # "gradient", "pattern", "texture", "photo", "abstract"
    tone_tags: List[str]  # "professional", "modern", "minimal", "vibrant", etc.
    file_path: Optional[str] = None  # Local file path
    url: Optional[str] = None  # Remote URL (for download)
    license: str = "Free"  # License type
    source: str = "local"  # "local", "unsplash", "pexels", "pixabay"
    width: int = 1920
    height: int = 1080
    dpi: int = 72


class BackgroundRegistry:
    """Registry of available background images"""
    
    def __init__(self):
        self._backgrounds: Dict[str, BackgroundImageInfo] = {}
        self._load_default_backgrounds()
    
    def _load_default_backgrounds(self):
        """Load default background definitions"""
        # These will be downloaded or generated
        backgrounds = [
            BackgroundImageInfo(
                image_id="gradient_blue_1",
                name="Blue Gradient",
                description="Professional blue gradient background",
                category="gradient",
                tone_tags=["professional", "formal"],
                file_path="assets/backgrounds/gradient_blue_1.png",
                license="Free",
                source="generated"
            ),
            BackgroundImageInfo(
                image_id="gradient_purple_1",
                name="Purple Gradient",
                description="Modern purple gradient background",
                category="gradient",
                tone_tags=["modern", "vibrant"],
                file_path="assets/backgrounds/gradient_purple_1.png",
                license="Free",
                source="generated"
            ),
            BackgroundImageInfo(
                image_id="solid_white",
                name="Solid White",
                description="Clean white background",
                category="solid",
                tone_tags=["minimal", "clean"],
                file_path="assets/backgrounds/solid_white.png",
                license="Free",
                source="generated"
            ),
            BackgroundImageInfo(
                image_id="pattern_dots_1",
                name="Dot Pattern",
                description="Subtle dot pattern background",
                category="pattern",
                tone_tags=["professional", "subtle"],
                file_path="assets/backgrounds/pattern_dots_1.png",
                license="Free",
                source="generated"
            )
        ]
        
        for bg in backgrounds:
            self._backgrounds[bg.image_id] = bg
    
    def get_background(self, image_id: str) -> Optional[BackgroundImageInfo]:
        """Get background by ID"""
        return self._backgrounds.get(image_id)
    
    def list_backgrounds(
        self,
        category: Optional[str] = None,
        tone_tags: Optional[List[str]] = None
    ) -> List[BackgroundImageInfo]:
        """List backgrounds with optional filters"""
        backgrounds = list(self._backgrounds.values())
        
        if category:
            backgrounds = [bg for bg in backgrounds if bg.category == category]
        
        if tone_tags:
            backgrounds = [
                bg for bg in backgrounds
                if any(tag in bg.tone_tags for tag in tone_tags)
            ]
        
        return backgrounds
    
    def get_background_path(self, image_id: str) -> Optional[str]:
        """Get file path for background image"""
        bg = self.get_background(image_id)
        if bg and bg.file_path:
            # Check if file exists
            path = Path(bg.file_path)
            if path.exists():
                return str(path.absolute())
        return None


# Singleton instance
background_registry = BackgroundRegistry()
