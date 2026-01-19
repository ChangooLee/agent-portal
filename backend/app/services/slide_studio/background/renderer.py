"""Background Renderer - Renders background CSS to PNG"""
import logging
from typing import Optional
from PIL import Image, ImageDraw
import re
from app.services.slide_studio.config import slide_studio_config

logger = logging.getLogger(__name__)


class BackgroundRenderer:
    """Renders CSS background to PNG image"""
    
    def __init__(self):
        self.slide_width = slide_studio_config.SLIDE_WIDTH
        self.slide_height = slide_studio_config.SLIDE_HEIGHT
    
    def render_css_to_png(self, css_background: str, output_path: str) -> str:
        """
        Render CSS background property to PNG.
        
        Supports:
        - solid colors: background: #ffffff;
        - gradients: background: linear-gradient(...);
        - patterns: (basic support)
        
        Args:
            css_background: CSS background property value
            output_path: Output PNG file path
            
        Returns:
            Path to generated PNG
        """
        try:
            # Parse CSS background
            if css_background.startswith("background:"):
                css_background = css_background.replace("background:", "").strip()
            
            # Create image
            img = Image.new("RGB", (self.slide_width, self.slide_height), color="#ffffff")
            draw = ImageDraw.Draw(img)
            
            # Parse and render
            if "linear-gradient" in css_background:
                img = self._render_gradient(css_background, img)
            elif css_background.startswith("#") or css_background.startswith("rgb"):
                img = self._render_solid_color(css_background, img)
            else:
                # Default to white
                img = Image.new("RGB", (self.slide_width, self.slide_height), color="#ffffff")
            
            # Save
            from pathlib import Path
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path, "PNG")
            
            logger.info(f"Rendered background PNG to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Background rendering failed: {e}")
            # Return white background as fallback
            img = Image.new("RGB", (self.slide_width, self.slide_height), color="#ffffff")
            from pathlib import Path
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path, "PNG")
            return output_path
    
    def _render_solid_color(self, color: str, img: Image.Image) -> Image.Image:
        """Render solid color background"""
        # Parse hex color
        if color.startswith("#"):
            rgb = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
        elif color.startswith("rgb"):
            # Parse rgb(...)
            match = re.search(r'rgb\((\d+),\s*(\d+),\s*(\d+)\)', color)
            if match:
                rgb = tuple(int(x) for x in match.groups())
            else:
                rgb = (255, 255, 255)
        else:
            rgb = (255, 255, 255)
        
        # Fill image
        img.paste(rgb, [0, 0, img.width, img.height])
        return img
    
    def _render_gradient(self, gradient_css: str, img: Image.Image) -> Image.Image:
        """Render linear gradient background"""
        try:
            # Parse gradient: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%)
            match = re.search(
                r'linear-gradient\((\d+)deg,\s*([^,]+)\s+(\d+)%,\s*([^)]+)\s+(\d+)%\)',
                gradient_css
            )
            
            if not match:
                # Try simpler format
                match = re.search(
                    r'linear-gradient\(([^,]+),\s*([^)]+)\)',
                    gradient_css
                )
                if match:
                    # Default to vertical gradient
                    color1 = match.group(1).strip()
                    color2 = match.group(2).strip()
                    return self._create_gradient(img, color1, color2, 180)
            
            if match:
                angle = int(match.group(1))
                color1 = match.group(2).strip()
                color2 = match.group(4).strip()
                return self._create_gradient(img, color1, color2, angle)
            
            # Fallback to solid color
            return self._render_solid_color("#ffffff", img)
            
        except Exception as e:
            logger.error(f"Gradient rendering failed: {e}")
            return self._render_solid_color("#ffffff", img)
    
    def _create_gradient(
        self,
        img: Image.Image,
        color1: str,
        color2: str,
        angle: int
    ) -> Image.Image:
        """Create gradient image"""
        from PIL import ImageFilter
        
        # Parse colors
        def parse_color(c: str) -> tuple:
            c = c.strip()
            if c.startswith("#"):
                return tuple(int(c[i:i+2], 16) for i in (1, 3, 5))
            elif "rgb" in c:
                match = re.search(r'rgb\((\d+),\s*(\d+),\s*(\d+)\)', c)
                if match:
                    return tuple(int(x) for x in match.groups())
            return (255, 255, 255)
        
        rgb1 = parse_color(color1)
        rgb2 = parse_color(color2)
        
        # Create gradient
        width, height = img.size
        
        # Simple horizontal/vertical gradient for now
        # Can be enhanced with angle support
        pixels = []
        for y in range(height):
            ratio = y / height
            r = int(rgb1[0] * (1 - ratio) + rgb2[0] * ratio)
            g = int(rgb1[1] * (1 - ratio) + rgb2[1] * ratio)
            b = int(rgb1[2] * (1 - ratio) + rgb2[2] * ratio)
            pixels.append((r, g, b))
        
        # Create gradient image
        gradient_img = Image.new("RGB", (width, height))
        for y in range(height):
            for x in range(width):
                gradient_img.putpixel((x, y), pixels[y])
        
        return gradient_img


# Singleton instance
background_renderer = BackgroundRenderer()
