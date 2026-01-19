"""Deck Planner - Creates slide plans from prompt"""
import logging
from typing import List, Optional
from app.services.slide_studio.ir.schema import SlidePlan, SlideType
from app.services.slide_studio.llm.client import slide_llm_client
from app.services.slide_studio.llm.json_repair import parse_with_retry

logger = logging.getLogger(__name__)


class DeckPlanner:
    """Plans deck structure using LLM"""
    
    async def plan_deck(
        self,
        prompt: str,
        slide_count: int = 10,
        goal: Optional[str] = None,
        audience: Optional[str] = None,
        tone: Optional[str] = None,
        trace_id: Optional[str] = None,
        **kwargs
    ) -> List[SlidePlan]:
        """
        Create slide plans from prompt using LLM.
        
        Args:
            prompt: User prompt/topic
            slide_count: Number of slides to generate
            goal: Optional goal
            audience: Optional audience
            tone: Optional tone
            **kwargs: Additional options
            
        Returns:
            List of SlidePlan objects
        """
        try:
            system_prompt = self._get_system_prompt()
            user_prompt = self._get_user_prompt(prompt, slide_count, goal, audience, tone)
            
            response = await slide_llm_client.generate_slide_content(
                slide_plan=None,  # Not needed for planning
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.7,
                max_tokens=3000,
                trace_id=trace_id
            )
            
            # Extract content from response
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # Parse JSON from content
            from app.services.slide_studio.llm.json_repair import repair_json
            parsed = repair_json(content)
            
            if not parsed or "slides" not in parsed:
                logger.warning("LLM response missing 'slides' field, using fallback")
                return self._fallback_plan(prompt, slide_count)
            
            # Convert to SlidePlan objects
            plans = []
            for i, slide_data in enumerate(parsed["slides"][:slide_count]):
                try:
                    slide_type_str = slide_data.get("slide_type", "BULLET").upper()
                    slide_type = SlideType[slide_type_str] if slide_type_str in SlideType.__members__ else SlideType.BULLET
                    
                    plan = SlidePlan(
                        slide_id=f"slide_{i+1:03d}",
                        title=slide_data.get("title", f"Slide {i+1}"),
                        slide_type=slide_type,
                        goal=slide_data.get("goal", goal or f"Present information about {prompt[:20]}")
                    )
                    plans.append(plan)
                    logger.debug(f"[plan_deck] Created SlidePlan #{i+1}: {plan.slide_id} - {plan.title} ({plan.slide_type.value})")
                except Exception as e:
                    logger.error(f"[plan_deck] Error parsing slide {i}: {e}")
                    # Add fallback slide
                    plans.append(SlidePlan(
                        slide_id=f"slide_{i+1:03d}",
                        title=f"Slide {i+1}: {prompt[:30]}...",
                        slide_type=SlideType.BULLET,
                        goal=goal or f"Present information about {prompt[:20]}"
                    ))
            
            # Ensure we have exactly slide_count slides
            while len(plans) < slide_count:
                logger.warning(f"[plan_deck] Not enough slides from LLM ({len(plans)}/{slide_count}), adding fallback slides")
                plans.append(SlidePlan(
                    slide_id=f"slide_{len(plans)+1:03d}",
                    title=f"Slide {len(plans)+1}: {prompt[:30]}...",
                    slide_type=SlideType.BULLET,
                    goal=goal or f"Present information about {prompt[:20]}"
                ))
            
            logger.info(f"[plan_deck] Created {len(plans[:slide_count])} slide plans")
            return plans[:slide_count]
            
        except Exception as e:
            logger.error(f"Deck planning failed: {e}, using fallback")
            return self._fallback_plan(prompt, slide_count)
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for deck planning"""
        return """You are a presentation deck planner. Your task is to create a logical structure for a presentation based on the user's topic.

You must return a JSON object with this exact structure:
{
  "slides": [
    {
      "title": "Slide title (clear and concise)",
      "slide_type": "TITLE|AGENDA|SECTION|BULLET|TWO_COLUMN|IMAGE|CHART|TABLE",
      "goal": "What this slide aims to achieve"
    },
    ...
  ]
}

Slide types:
- TITLE: Opening slide with main topic
- AGENDA: Table of contents / agenda
- SECTION: Section divider / chapter title
- BULLET: Bullet point list
- TWO_COLUMN: Two-column layout
- IMAGE: Image-focused slide
- CHART: Data visualization slide
- TABLE: Table-based slide

Create a logical flow: Title → Agenda → Sections → Content slides → Conclusion.
Ensure variety in slide types for visual interest."""
    
    def _get_user_prompt(
        self,
        prompt: str,
        slide_count: int,
        goal: Optional[str] = None,
        audience: Optional[str] = None,
        tone: Optional[str] = None
    ) -> str:
        """Get user prompt for deck planning"""
        user_prompt = f"""Create a presentation deck structure with {slide_count} slides.

Topic: {prompt}
"""
        if goal:
            user_prompt += f"Goal: {goal}\n"
        if audience:
            user_prompt += f"Audience: {audience}\n"
        if tone:
            user_prompt += f"Tone: {tone}\n"
        
        user_prompt += "\nGenerate a logical sequence of slides that covers the topic comprehensively. Return only valid JSON."
        
        return user_prompt
    
    def _fallback_plan(self, prompt: str, slide_count: int) -> List[SlidePlan]:
        """Fallback plan if LLM fails"""
        plans = []
        slide_types = [
            SlideType.TITLE,
            SlideType.AGENDA,
            SlideType.SECTION,
            SlideType.BULLET,
            SlideType.TWO_COLUMN,
            SlideType.IMAGE,
            SlideType.CHART,
            SlideType.TABLE,
            SlideType.BULLET,
            SlideType.SECTION
        ]
        
        for i in range(slide_count):
            slide_type = slide_types[i % len(slide_types)]
            plans.append(SlidePlan(
                slide_id=f"slide_{i+1:03d}",
                title=f"Slide {i+1}: {prompt[:30]}...",
                slide_type=slide_type,
                goal=f"Present information about {prompt[:20]}"
            ))
        
        return plans


# Singleton instance
deck_planner = DeckPlanner()
