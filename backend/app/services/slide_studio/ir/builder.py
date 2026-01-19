"""Slide Builder - SlidePlan -> SlideIR"""
import logging
from typing import Optional
from app.services.slide_studio.ir.schema import SlideIR, SlidePlan, SlideStage, TextSlot, BulletSlot, ImageSlot, ChartSlot, TableSlot
from app.services.slide_studio.image.provider import ImageProviderChain
from app.services.slide_studio.image.user_provided import UserProvidedImageProvider
from app.services.slide_studio.image.local_asset import LocalAssetLibraryProvider
from app.services.slide_studio.image.icon_composer import IconComposerProvider
from app.services.slide_studio.image.chart_renderer import ChartRendererProvider
from app.services.slide_studio.image.placeholder import PlaceholderProvider
from app.services.slide_studio.image.flux_client import FluxProvider
from app.services.slide_studio.llm.client import slide_llm_client
from app.services.slide_studio.llm.prompts import get_slide_builder_system_prompt, get_slide_builder_user_prompt
from app.services.slide_studio.llm.json_repair import parse_with_retry

logger = logging.getLogger(__name__)


class SlideBuilder:
    """Builds SlideIR from SlidePlan using LLM"""
    
    def __init__(self):
        # Initialize image provider chain
        self.image_provider_chain = ImageProviderChain([
            UserProvidedImageProvider(),
            LocalAssetLibraryProvider(),
            IconComposerProvider(),
            ChartRendererProvider(),
            PlaceholderProvider(),
            FluxProvider()  # Last (optional)
        ])
    
    async def build_slide(
        self,
        slide_plan: SlidePlan,
        goal: Optional[str] = None,
        audience: Optional[str] = None,
        tone: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> SlideIR:
        """
        Build SlideIR from SlidePlan using LLM.
        
        Args:
            slide_plan: SlidePlan
            goal: Optional goal
            audience: Optional audience
            tone: Optional tone
            
        Returns:
            SlideIR
        """
        try:
            # Try LLM-based generation first
            logger.info(f"[{slide_plan.slide_id}] build_slide: Calling LLM for slide content generation")
            logger.debug(f"[{slide_plan.slide_id}] build_slide: SlidePlan - title: {slide_plan.title}, type: {slide_plan.slide_type.value}, goal: {slide_plan.goal}")
            slide_ir = await self.build_slide_with_llm(slide_plan, goal, audience, tone, trace_id)
            if slide_ir:
                logger.info(f"[{slide_plan.slide_id}] build_slide: LLM generation successful, {len(slide_ir.slots)} slots created")
                return slide_ir
        except Exception as e:
            logger.warning(f"[{slide_plan.slide_id}] build_slide: LLM slide building failed: {e}, using fallback", exc_info=True)
        
        # Fallback to simple structure
        slots = {}
        
        # Create basic slots based on slide type
        if slide_plan.slide_type.value in ["TITLE", "SECTION"]:
            slots["title"] = TextSlot(
                content=slide_plan.title,
                style=None
            )
        elif slide_plan.slide_type.value == "BULLET":
            slots["title"] = TextSlot(content=slide_plan.title)
            slots["content"] = BulletSlot(
                items=[
                    f"Key point 1 about {slide_plan.title}",
                    f"Key point 2 about {slide_plan.title}",
                    f"Key point 3 about {slide_plan.title}"
                ]
            )
        elif slide_plan.slide_type.value == "TWO_COLUMN":
            slots["title"] = TextSlot(content=slide_plan.title)
            slots["left"] = BulletSlot(items=["Left column item 1", "Left column item 2"])
            slots["right"] = BulletSlot(items=["Right column item 1", "Right column item 2"])
        else:
            slots["title"] = TextSlot(content=slide_plan.title)
            slots["content"] = TextSlot(content=f"Content for {slide_plan.title}")
        
        # Process image slots with provider chain
        for slot_id, slot in slots.items():
            if isinstance(slot, ImageSlot) and not slot.image_url:
                context = {
                    "slide_type": slide_plan.slide_type.value,
                    "keywords": [slide_plan.title]
                }
                image_url = await self.image_provider_chain.get_image(slot, context)
                if image_url:
                    slot.image_url = image_url
        
        return SlideIR(
            slide_id=slide_plan.slide_id,
            title=slide_plan.title,
            slide_type=slide_plan.slide_type,
            slots=slots
            # stage will use default (PLANNED) and be updated by orchestrator
        )
    
    async def build_slide_with_llm(
        self,
        slide_plan: SlidePlan,
        goal: Optional[str] = None,
        audience: Optional[str] = None,
        tone: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> Optional[SlideIR]:
        """
        Build SlideIR using LLM.
        
        Args:
            slide_plan: SlidePlan
            goal: Optional goal
            audience: Optional audience
            tone: Optional tone
            
        Returns:
            SlideIR or None if failed
        """
        try:
            system_prompt = get_slide_builder_system_prompt(slide_plan.slide_type)
            user_prompt = get_slide_builder_user_prompt(slide_plan, goal, audience, tone)
            
            logger.info(f"[{slide_plan.slide_id}] build_slide_with_llm: Calling LLM - slide_type: {slide_plan.slide_type.value}, title: {slide_plan.title}")
            logger.debug(f"[{slide_plan.slide_id}] build_slide_with_llm: System prompt length: {len(system_prompt)}, User prompt length: {len(user_prompt)}")
            logger.debug(f"[{slide_plan.slide_id}] build_slide_with_llm: User prompt preview: {user_prompt[:300]}...")
            
            response = await slide_llm_client.generate_slide_content(
                slide_plan=slide_plan,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.7,
                max_tokens=2000,
                trace_id=trace_id
            )
            
            logger.info(f"[{slide_plan.slide_id}] build_slide_with_llm: LLM response received - choices: {len(response.get('choices', []))}")
            
            # Extract content from response
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            logger.debug(f"[{slide_plan.slide_id}] build_slide_with_llm: Response content length: {len(content)}, preview: {content[:300]}...")
            
            # Parse JSON from content
            from app.services.slide_studio.llm.json_repair import repair_json
            parsed = repair_json(content)
            
            if not parsed or "slots" not in parsed:
                logger.warning(f"[{slide_plan.slide_id}] build_slide_with_llm: LLM response missing 'slots' field, parsed keys: {list(parsed.keys()) if parsed else 'None'}")
                return None
            
            logger.info(f"[{slide_plan.slide_id}] build_slide_with_llm: Parsed {len(parsed.get('slots', {}))} slots from LLM response")
            
            # Build slots from parsed JSON
            slots = {}
            for slot_id, slot_data in parsed.get("slots", {}).items():
                slot_type = slot_data.get("slot_type", "text")
                
                if slot_type == "text":
                    content = slot_data.get("content", "")
                    slots[slot_id] = TextSlot(
                        content=content,
                        style=None
                    )
                    logger.debug(f"[{slide_plan.slide_id}] build_slide_with_llm: Created TextSlot '{slot_id}' with {len(content)} chars")
                elif slot_type == "bullet":
                    items = slot_data.get("items", [])
                    slots[slot_id] = BulletSlot(
                        items=items
                    )
                    logger.debug(f"[{slide_plan.slide_id}] build_slide_with_llm: Created BulletSlot '{slot_id}' with {len(items)} items")
                elif slot_type == "image":
                    slots[slot_id] = ImageSlot(
                        alt_text=slot_data.get("alt_text", "")
                    )
                    logger.debug(f"[{slide_plan.slide_id}] build_slide_with_llm: Created ImageSlot '{slot_id}'")
                elif slot_type == "chart":
                    slots[slot_id] = ChartSlot(
                        chart_type=slot_data.get("chart_type", "bar"),
                        data=slot_data.get("data", {})
                    )
                    logger.debug(f"[{slide_plan.slide_id}] build_slide_with_llm: Created ChartSlot '{slot_id}'")
                elif slot_type == "table":
                    slots[slot_id] = TableSlot(
                        headers=slot_data.get("headers", []),
                        rows=slot_data.get("rows", [])
                    )
                    logger.debug(f"[{slide_plan.slide_id}] build_slide_with_llm: Created TableSlot '{slot_id}'")
            
            # Process image slots with provider chain
            for slot_id, slot in slots.items():
                if isinstance(slot, ImageSlot) and not slot.image_url:
                    context = {
                        "slide_type": slide_plan.slide_type.value,
                        "keywords": [slide_plan.title, parsed.get("title", "")]
                    }
                    logger.debug(f"[{slide_plan.slide_id}] build_slide_with_llm: Processing image slot '{slot_id}' with context: {context}")
                    image_url = await self.image_provider_chain.get_image(slot, context)
                    if image_url:
                        slot.image_url = image_url
                        logger.info(f"[{slide_plan.slide_id}] build_slide_with_llm: Image URL obtained for slot '{slot_id}': {image_url[:50]}...")
            
            slide_title = parsed.get("title", slide_plan.title)
            logger.info(f"[{slide_plan.slide_id}] build_slide_with_llm: SlideIR created - title: {slide_title}, {len(slots)} slots")
            
            return SlideIR(
                slide_id=slide_plan.slide_id,
                title=slide_title,
                slide_type=slide_plan.slide_type,
                slots=slots
                # stage will use default (PLANNED) and be updated by orchestrator
            )
            
        except Exception as e:
            logger.error(f"LLM slide building failed: {e}", exc_info=True)
            return None
    
    async def build_slide_with_improvements(
        self,
        slide_plan: SlidePlan,
        current_slide_ir: SlideIR,
        issues: list,
        reasoning: str = "",
        goal: Optional[str] = None,
        audience: Optional[str] = None,
        tone: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> Optional[SlideIR]:
        """
        Rebuild slide with improvements based on issues and suggestions.
        
        This is called during reflection loop to improve slide quality.
        
        Args:
            slide_plan: Original SlidePlan
            current_slide_ir: Current SlideIR with issues
            issues: List of issues found
            reasoning: Reasoning from reflector
            goal: Optional goal
            audience: Optional audience
            tone: Optional tone
            
        Returns:
            Improved SlideIR or None if failed
        """
        try:
            from app.services.slide_studio.llm.prompts import get_slide_improvement_prompt
            
            logger.info(f"[{slide_plan.slide_id}] build_slide_with_improvements: Starting LLM-based improvement with {len(issues)} issues")
            logger.debug(f"[{slide_plan.slide_id}] build_slide_with_improvements: Issues: {[i.get('type') + ':' + i.get('message', '')[:50] for i in issues[:5]]}")
            logger.debug(f"[{slide_plan.slide_id}] build_slide_with_improvements: Reasoning: {reasoning[:200] if reasoning else 'None'}...")
            
            # Build improvement prompt with issues context
            improvement_prompt = get_slide_improvement_prompt(
                slide_plan,
                current_slide_ir,
                issues,
                reasoning,
                goal,
                audience,
                tone
            )
            
            system_prompt = get_slide_builder_system_prompt(slide_plan.slide_type)
            
            logger.debug(f"[{slide_plan.slide_id}] build_slide_with_improvements: System prompt length: {len(system_prompt)}, Improvement prompt length: {len(improvement_prompt)}")
            logger.debug(f"[{slide_plan.slide_id}] build_slide_with_improvements: Improvement prompt preview: {improvement_prompt[:300]}...")
            
            response = await slide_llm_client.generate_slide_content(
                slide_plan=slide_plan,
                system_prompt=system_prompt,
                user_prompt=improvement_prompt,
                temperature=0.7,
                max_tokens=2000,
                trace_id=trace_id
            )
            
            logger.info(f"[{slide_plan.slide_id}] build_slide_with_improvements: LLM response received - choices: {len(response.get('choices', []))}")
            
            # Extract content from response
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            logger.debug(f"[{slide_plan.slide_id}] build_slide_with_improvements: Response content length: {len(content)}, preview: {content[:300]}...")
            
            # Parse JSON from content
            from app.services.slide_studio.llm.json_repair import repair_json
            parsed = repair_json(content)
            
            if not parsed or "slots" not in parsed:
                logger.warning(f"[{slide_plan.slide_id}] build_slide_with_improvements: LLM improvement response missing 'slots' field, parsed keys: {list(parsed.keys()) if parsed else 'None'}")
                return None
            
            logger.info(f"[{slide_plan.slide_id}] build_slide_with_improvements: Parsed {len(parsed.get('slots', {}))} slots from LLM response")
            
            # Build slots from parsed JSON
            slots = {}
            for slot_id, slot_data in parsed.get("slots", {}).items():
                slot_type = slot_data.get("slot_type", "text")
                
                if slot_type == "text":
                    slots[slot_id] = TextSlot(
                        content=slot_data.get("content", ""),
                        style=None
                    )
                elif slot_type == "bullet":
                    slots[slot_id] = BulletSlot(
                        items=slot_data.get("items", [])
                    )
                elif slot_type == "image":
                    slots[slot_id] = ImageSlot(
                        alt_text=slot_data.get("alt_text", "")
                    )
                elif slot_type == "chart":
                    slots[slot_id] = ChartSlot(
                        chart_type=slot_data.get("chart_type", "bar"),
                        data=slot_data.get("data", {})
                    )
                elif slot_type == "table":
                    slots[slot_id] = TableSlot(
                        headers=slot_data.get("headers", []),
                        rows=slot_data.get("rows", [])
                    )
            
            # Process image slots with provider chain
            for slot_id, slot in slots.items():
                if isinstance(slot, ImageSlot) and not slot.image_url:
                    context = {
                        "slide_type": slide_plan.slide_type.value,
                        "keywords": [slide_plan.title, parsed.get("title", "")]
                    }
                    logger.debug(f"[{slide_plan.slide_id}] build_slide_with_improvements: Processing image slot '{slot_id}' with context: {context}")
                    image_url = await self.image_provider_chain.get_image(slot, context)
                    if image_url:
                        slot.image_url = image_url
                        logger.info(f"[{slide_plan.slide_id}] build_slide_with_improvements: Image URL obtained for slot '{slot_id}': {image_url[:50]}...")
            
            slide_title = parsed.get("title", slide_plan.title)
            logger.info(f"[{slide_plan.slide_id}] build_slide_with_improvements: Improved SlideIR created - title: {slide_title}, {len(slots)} slots")
            
            return SlideIR(
                slide_id=slide_plan.slide_id,
                title=slide_title,
                slide_type=slide_plan.slide_type,
                slots=slots,
                stage=SlideStage.PLANNED
            )
            
        except Exception as e:
            logger.error(f"LLM slide improvement failed: {e}", exc_info=True)
            return None


# Singleton instance
slide_builder = SlideBuilder()
