"""Preview Renderer - IR + Layout -> HTML/SVG"""
from typing import Optional
from app.services.slide_studio.ir.schema import SlideIR
from app.services.slide_studio.layout.tokens import default_tokens
from app.services.slide_studio.config import slide_studio_config


class PreviewRenderer:
    """Renders slide IR to HTML/SVG preview"""
    
    def __init__(self):
        self.slide_width = slide_studio_config.SLIDE_WIDTH
        self.slide_height = slide_studio_config.SLIDE_HEIGHT
    
    def render_html(self, slide_ir: SlideIR) -> str:
        """
        Render slide IR to HTML.
        
        Args:
            slide_ir: Slide IR with layout
            
        Returns:
            HTML string (full document)
        """
        # Get background style (if available)
        background_style = self._get_background_style(slide_ir)
        
        # Render slots
        slots_html = []
        for slot_id, slot in slide_ir.slots.items():
            if slot.bbox:
                slots_html.append(self._render_slot(slot, slot.bbox))
        
        # Build full HTML document
        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Slide Preview</title>
    <style>
        {self._get_font_face_css()}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: {default_tokens.font_families["default"]};
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            text-rendering: optimizeLegibility;
            overflow: hidden;
        }}
        
        .slide-preview {{
            width: {self.slide_width}px;
            height: {self.slide_height}px;
            position: relative;
            overflow: hidden;
            {background_style}
        }}
        
        .slot-text, .slot-bullet {{
            word-wrap: break-word;
            word-break: keep-all;
            overflow-wrap: break-word;
            font-family: {default_tokens.font_families["body"]};
        }}
        
        .slot-text {{
            white-space: pre-wrap;
        }}
        
        .slot-bullet {{
            list-style-position: outside;
            padding-left: 1.5em;
        }}
        
        .slot-bullet li {{
            margin-bottom: 0.5em;
            word-wrap: break-word;
            word-break: keep-all;
        }}
        
        .slot-table {{
            border-collapse: collapse;
            width: 100%;
        }}
        
        .slot-table th, .slot-table td {{
            border: 1px solid #e5e7eb;
            padding: 0.5em;
            text-align: left;
        }}
        
        .slot-table th {{
            background-color: #f3f4f6;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="slide-preview">
        {''.join(slots_html)}
    </div>
</body>
</html>"""
        return html
    
    def _get_font_face_css(self) -> str:
        """Generate @font-face CSS for local fonts"""
        from app.services.slide_studio.assets.fonts.registry import font_registry
        
        # Generate @font-face for all available fonts
        css_parts = []
        
        # Primary Korean fonts
        for font_id in ["pretendard", "noto_sans_kr", "nanum_gothic"]:
            font_css = font_registry.generate_font_face_css(font_id)
            if font_css:
                css_parts.append(font_css)
        
        # Fallback fonts
        css_parts.append("""
        /* System font fallbacks */
        @font-face {
            font-family: 'System Fallback';
            src: local('-apple-system'), local('BlinkMacSystemFont'), 
                 local('Segoe UI'), local('Roboto'), local('Arial');
            font-display: swap;
        }""")
        
        return "\n".join(css_parts) if css_parts else ""
    
    def _get_background_style(self, slide_ir: SlideIR) -> str:
        """Get CSS background style for slide from theme"""
        from app.services.slide_studio.store.repo import slide_studio_repo
        from app.services.slide_studio.theme.registry import theme_registry
        
        # Find deck IR that contains this slide
        deck_ir = None
        for deck_id in slide_studio_repo._deck_irs.keys():
            candidate = slide_studio_repo.get_deck_ir(deck_id)
            if candidate and any(s.slide_id == slide_ir.slide_id for s in candidate.slides):
                deck_ir = candidate
                break
        
        if deck_ir and deck_ir.theme_id:
            theme = theme_registry.get_theme(deck_ir.theme_id)
            variant_id = deck_ir.theme_variant_map.get(slide_ir.slide_type.value)
            if variant_id:
                variant = theme_registry.get_variant_for_slide_type(
                    deck_ir.theme_id,
                    slide_ir.slide_type.value,
                    variant_id
                )
                return variant.css
        
        # Fallback to default
        return f"background: {default_tokens.background_color};"
    
    def _render_slot(self, slot, bbox) -> str:
        """Render a single slot"""
        base_style = f'position: absolute; left: {bbox.x}px; top: {bbox.y}px; width: {bbox.w}px; height: {bbox.h}px;'
        
        if slot.slot_type == "text":
            content = slot.content.replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')
            font_size = slot.style.font_size if slot.style and slot.style.font_size else default_tokens.font_sizes["body"]
            color = slot.style.color if slot.style and slot.style.color else default_tokens.text_color
            font_family = slot.style.font_family if slot.style and slot.style.font_family else default_tokens.font_families["body"]
            font_weight = slot.style.font_weight if slot.style and slot.style.font_weight else default_tokens.font_weights["normal"]
            line_height = slot.style.line_height if slot.style and slot.style.line_height else default_tokens.line_heights["normal"]
            align = slot.style.align if slot.style and slot.style.align else "left"
            
            style = f'{base_style} font-size: {font_size}px; color: {color}; font-family: {font_family}; font-weight: {font_weight}; line-height: {line_height}; text-align: {align};'
            return f'<div class="slot-text" style="{style}">{content}</div>'
        
        elif slot.slot_type == "bullet":
            items_html = ''.join([
                f'<li style="word-wrap: break-word; word-break: keep-all;">{item.replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")}</li>' 
                for item in slot.items
            ])
            font_size = slot.style.font_size if slot.style and slot.style.font_size else default_tokens.font_sizes["body"]
            color = slot.style.color if slot.style and slot.style.color else default_tokens.text_color
            font_family = slot.style.font_family if slot.style and slot.style.font_family else default_tokens.font_families["body"]
            font_weight = slot.style.font_weight if slot.style and slot.style.font_weight else default_tokens.font_weights["normal"]
            line_height = slot.style.line_height if slot.style and slot.style.line_height else default_tokens.line_heights["normal"]
            
            style = f'{base_style} font-size: {font_size}px; color: {color}; font-family: {font_family}; font-weight: {font_weight}; line-height: {line_height};'
            return f'<ul class="slot-bullet" style="{style}">{items_html}</ul>'
        
        elif slot.slot_type == "image":
            if slot.image_url:
                return f'<img class="slot-image" src="{slot.image_url}" alt="{slot.alt_text or ""}" style="{base_style} object-fit: contain;" />'
            else:
                return f'<div class="slot-image-placeholder" style="{base_style} background: #f3f4f6; display: flex; align-items: center; justify-content: center; color: #9ca3af;">Image</div>'
        
        elif slot.slot_type == "chart":
            return f'<div class="slot-chart" style="{base_style} background: #f3f4f6; display: flex; align-items: center; justify-content: center; color: #9ca3af;">Chart: {slot.chart_type}</div>'
        
        elif slot.slot_type == "table":
            def escape_html(text):
                return str(text).replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")
            
            headers_html = ''.join([f'<th>{escape_html(h)}</th>' for h in slot.headers])
            rows_html = ''.join([
                f'<tr>{"".join([f"<td>{escape_html(cell)}</td>" for cell in row])}</tr>'
                for row in slot.rows
            ])
            return f'<table class="slot-table" style="{base_style}"><thead><tr>{headers_html}</tr></thead><tbody>{rows_html}</tbody></table>'
        
        return f'<div class="slot-unknown" style="{base_style}">Unknown slot type</div>'
    
    def render_thumbnail(self, slide_ir: SlideIR) -> Optional[str]:
        """
        Render slide to thumbnail (data URI).
        
        For Step 2, returns None (placeholder).
        In Step 4+, this will use PIL to generate actual thumbnail image.
        
        Args:
            slide_ir: Slide IR
            
        Returns:
            Data URI string or None
        """
        # TODO: Implement PIL-based thumbnail generation in Step 4
        return None


# Singleton instance
preview_renderer = PreviewRenderer()
