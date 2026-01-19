"""Design Tokens - Font, Color, Typography, Spacing"""
from typing import Dict, Optional
from pydantic import BaseModel


class FontProfile(BaseModel):
    """Font profile for text rendering"""
    family: str
    height_factor: float = 1.2  # Height multiplier for Korean text
    avg_char_width_factor: float = 1.1  # Character width multiplier
    os: str = "linux"  # linux, windows, mac


class DesignTokens(BaseModel):
    """Design tokens for consistent styling"""
    
    # Slide dimensions
    slide_width: int = 1920
    slide_height: int = 1080
    
    # Colors
    primary_color: str = "#6366f1"  # Indigo
    secondary_color: str = "#8b5cf6"  # Purple
    text_color: str = "#1f2937"  # Gray-800
    background_color: str = "#ffffff"  # White
    
    # Typography
    font_families: Dict[str, str] = {
        "default": "'Pretendard', 'Noto Sans KR', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        "heading": "'Pretendard', 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif",
        "body": "'Pretendard', 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif"
    }
    
    font_sizes: Dict[str, int] = {
        "h1": 48,
        "h2": 36,
        "h3": 28,
        "body": 18,
        "small": 14
    }
    
    font_weights: Dict[str, str] = {
        "normal": "400",
        "medium": "500",
        "semibold": "600",
        "bold": "700"
    }
    
    line_heights: Dict[str, float] = {
        "tight": 1.2,
        "normal": 1.5,
        "relaxed": 1.8
    }
    
    # Spacing
    spacing: Dict[str, int] = {
        "xs": 4,
        "sm": 8,
        "md": 16,
        "lg": 24,
        "xl": 32,
        "2xl": 48,
        "grid": 8  # Grid snap size
    }
    
    # Safe margins (percentage)
    safe_margins: Dict[str, float] = {
        "title": 0.20,  # 20%
        "bullet": 0.15,  # 15%
        "table": 0.25,  # 25%
        "default": 0.15  # 15%
    }
    
    # Font profiles (Korean text correction)
    font_profiles: Dict[str, FontProfile] = {
        "pretendard": FontProfile(
            family="Pretendard",
            height_factor=1.3,
            avg_char_width_factor=1.15,
            os="linux"
        ),
        "noto": FontProfile(
            family="Noto Sans KR",
            height_factor=1.25,
            avg_char_width_factor=1.12,
            os="linux"
        )
    }


# Default design tokens instance
default_tokens = DesignTokens()
