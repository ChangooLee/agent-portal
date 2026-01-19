"""Font Registry - Available fonts with metadata"""
from typing import Dict, List, Optional
from pydantic import BaseModel


class FontInfo(BaseModel):
    """Font information"""
    font_id: str
    family_name: str
    display_name: str
    license: str  # OFL, SIL, Apache, etc.
    source: str  # "google_fonts", "local", "custom"
    woff2_url: Optional[str] = None
    woff_url: Optional[str] = None
    ttf_url: Optional[str] = None
    local_path: Optional[str] = None  # Path to local font file
    supports_korean: bool = True
    weights: List[str] = ["400", "500", "600", "700"]  # Available font weights
    styles: List[str] = ["normal"]  # normal, italic


class FontRegistry:
    """Registry of available fonts"""
    
    def __init__(self):
        self._fonts: Dict[str, FontInfo] = {}
        self._load_default_fonts()
    
    def _load_default_fonts(self):
        """Load default font definitions"""
        # Pretendard (local)
        pretendard = FontInfo(
            font_id="pretendard",
            family_name="Pretendard",
            display_name="Pretendard",
            license="OFL",
            source="local",
            local_path="/api/slides/assets/fonts/pretendard/Pretendard-Regular.woff2",
            supports_korean=True,
            weights=["400", "500", "700"],  # Only downloaded weights
            styles=["normal"]
        )
        
        # Noto Sans KR (local)
        noto_sans_kr = FontInfo(
            font_id="noto_sans_kr",
            family_name="Noto Sans KR",
            display_name="Noto Sans KR",
            license="OFL",
            source="local",
            local_path="/api/slides/assets/fonts/noto-sans-kr/NotoSansKR-Regular.woff2",
            supports_korean=True,
            weights=["400", "700"],  # Only downloaded weights
            styles=["normal"]
        )
        
        # Nanum Gothic (local)
        nanum_gothic = FontInfo(
            font_id="nanum_gothic",
            family_name="Nanum Gothic",
            display_name="Nanum Gothic",
            license="OFL",
            source="local",
            local_path="/api/slides/assets/fonts/nanum-gothic/NanumGothic-Regular.woff2",
            supports_korean=True,
            weights=["400", "700"],  # Only downloaded weights
            styles=["normal"]
        )
        
        # Nanum Myeongjo (local)
        nanum_myeongjo = FontInfo(
            font_id="nanum_myeongjo",
            family_name="Nanum Myeongjo",
            display_name="Nanum Myeongjo",
            license="OFL",
            source="local",
            local_path="/api/slides/assets/fonts/nanum-myeongjo/NanumMyeongjo-Regular.woff2",
            supports_korean=True,
            weights=["400", "700"],  # Only downloaded weights
            styles=["normal"]
        )
        
        # Inter (English, good fallback)
        inter = FontInfo(
            font_id="inter",
            family_name="Inter",
            display_name="Inter",
            license="OFL",
            source="google_fonts",
            woff2_url="https://fonts.googleapis.com/css2?family=Inter:wght@100;200;300;400;500;600;700;800;900&display=swap",
            supports_korean=False,
            weights=["100", "200", "300", "400", "500", "600", "700", "800", "900"],
            styles=["normal", "italic"]
        )
        
        self._fonts["pretendard"] = pretendard
        self._fonts["noto_sans_kr"] = noto_sans_kr
        self._fonts["nanum_gothic"] = nanum_gothic
        self._fonts["nanum_myeongjo"] = nanum_myeongjo
        self._fonts["inter"] = inter
    
    def get_font(self, font_id: str) -> Optional[FontInfo]:
        """Get font by ID"""
        return self._fonts.get(font_id)
    
    def list_fonts(self, korean_only: bool = False) -> List[FontInfo]:
        """List all fonts"""
        fonts = list(self._fonts.values())
        if korean_only:
            fonts = [f for f in fonts if f.supports_korean]
        return fonts
    
    def generate_font_face_css(self, font_id: str) -> str:
        """Generate @font-face CSS for a font"""
        font = self.get_font(font_id)
        if not font:
            return ""
        
        css_parts = []
        
        for weight in font.weights:
            for style in font.styles:
                font_family = font.family_name
                font_style = style
                font_weight = weight
                
                # Build src
                src_parts = []
                
                # Local font first
                if font.local_path:
                    src_parts.append(f"url('{font.local_path}') format('woff2')")
                
                # Web font fallback
                if font.woff2_url:
                    # For Google Fonts, we'll use the CDN link directly
                    # But for local serving, we need the actual font file URL
                    pass
                
                # System font fallback
                src_parts.append(f"local('{font_family}')")
                
                if not src_parts:
                    continue
                
                src = ", ".join(src_parts)
                
                css = f"""
        @font-face {{
            font-family: '{font_family}';
            font-style: {font_style};
            font-weight: {font_weight};
            src: {src};
            font-display: swap;
        }}"""
                css_parts.append(css)
        
        return "\n".join(css_parts)


# Singleton instance
font_registry = FontRegistry()
