"""Theme Selector - LLM-based theme selection"""
import logging
from typing import Optional
from app.services.slide_studio.theme.registry import theme_registry
from app.services.slide_studio.theme.schema import Theme
from app.services.slide_studio.llm.client import slide_llm_client
from app.services.slide_studio.llm.json_repair import parse_with_retry
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ThemeSelection(BaseModel):
    """Theme selection result"""
    theme_id: str
    reasoning: str


class ThemeSelector:
    """Selects theme based on prompt and tone"""
    
    def __init__(self):
        self.registry = theme_registry
    
    async def select_theme(
        self,
        prompt: str,
        goal: Optional[str] = None,
        audience: Optional[str] = None,
        tone: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> Theme:
        """
        Select theme based on prompt and context.
        
        Args:
            prompt: User prompt
            goal: Presentation goal
            audience: Target audience
            tone: Desired tone
            
        Returns:
            Selected Theme
        """
        try:
            # Get available themes
            themes = self.registry.list_themes()
            theme_descriptions = "\n".join([
                f"- {t.theme_id}: {t.name} - {t.description}"
                for t in themes
            ])
            
            # LLM-based selection
            system_prompt = f"""You are a design expert selecting a presentation theme.

Available themes:
{theme_descriptions}

Select the most appropriate theme based on the user's prompt, goal, audience, and tone.
Return JSON with theme_id and reasoning."""
            
            user_prompt = f"""Prompt: {prompt}
Goal: {goal or "Not specified"}
Audience: {audience or "General"}
Tone: {tone or "Professional"}

Select the best theme and explain why."""
            
            response = await slide_llm_client.chat_completion_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=200,
                trace_id=trace_id,
                node_name="theme_selector"
            )
            
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            selection = parse_with_retry(content, ThemeSelection)
            
            if selection and selection.theme_id in [t.theme_id for t in themes]:
                logger.info(f"Theme selected: {selection.theme_id} - {selection.reasoning}")
                return self.registry.get_theme(selection.theme_id)
            else:
                logger.warning("LLM theme selection failed, using default professional theme")
                return self.registry.get_theme("professional")
                
        except Exception as e:
            logger.error(f"Theme selection failed: {e}, using default")
            return self.registry.get_theme("professional")
    
    def select_variant_for_slide_type(
        self,
        theme: Theme,
        slide_type: str,
        tone_tags: Optional[list] = None
    ) -> str:
        """
        Select background variant for slide type.
        
        Args:
            theme: Selected theme
            slide_type: Slide type
            tone_tags: Preferred tone tags
            
        Returns:
            Variant ID
        """
        variants = theme.background_variants.get(slide_type, theme.background_variants.get("BULLET", []))
        
        if not variants:
            return "default"
        
        # If tone_tags provided, try to match
        if tone_tags:
            for variant in variants:
                if any(tag in variant.tone_tags for tag in tone_tags):
                    return variant.variant_id
        
        # Return first variant
        return variants[0].variant_id


# Singleton instance
theme_selector = ThemeSelector()
