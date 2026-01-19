"""Slide Studio Configuration"""
from app.config import get_settings

settings = get_settings()


class SlideStudioConfig:
    """Configuration for Slide Studio"""
    
    # LLM Model (use LiteLLM model_name from config/litellm.yaml)
    LLM_MODEL: str = getattr(settings, 'SLIDE_STUDIO_LLM_MODEL', 'qwen-235b')  # Default to qwen-235b (Primary model)
    
    # Concurrency limits
    MAX_CONCURRENT_SLIDES: int = 3  # Maximum concurrent slide generation
    MAX_CONCURRENT_IMAGES: int = 2  # Maximum concurrent image generation
    MAX_CONCURRENT_PPTX: int = 1  # Maximum concurrent PPTX generation
    
    # Reflection loop limits
    MAX_REFLECTION_LOOPS: int = 2  # Maximum automatic reflection loops
    MIN_SCORE_THRESHOLD: int = 85  # Minimum score to proceed without reflection
    
    # Quality targets
    TARGET_NATIVE_TEXT_RATIO: float = 0.7  # Target native text ratio
    MIN_FONT_SIZE: int = 14  # Minimum font size in pixels
    
    # Slide dimensions (16:9)
    SLIDE_WIDTH: int = 1920  # pixels
    SLIDE_HEIGHT: int = 1080  # pixels
    
    # Safe margins (percentage)
    TITLE_SAFE_MARGIN: float = 0.20  # 20%
    BULLET_SAFE_MARGIN: float = 0.15  # 15%
    TABLE_SAFE_MARGIN: float = 0.25  # 25%
    
    # Storage
    ARTIFACT_STORAGE_PATH: str = "/data/slide-studio/artifacts"  # PPTX/PDF storage
    ASSET_LIBRARY_PATH: str = "/data/slide-studio/assets"  # Asset library path


slide_studio_config = SlideStudioConfig()
