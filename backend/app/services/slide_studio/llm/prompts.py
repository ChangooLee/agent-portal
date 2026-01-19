"""Prompts for slide generation"""
from typing import Optional
from app.services.slide_studio.ir.schema import SlideType


def get_slide_builder_system_prompt(slide_type: SlideType) -> str:
    """Get system prompt for slide builder"""
    base_prompt = """You are a professional slide content generator. Generate high-quality slide content in JSON format.

You must return a JSON object with this exact structure:
{
  "title": "Slide title (clear and engaging)",
  "slots": {
    "slot_id": {
      "slot_type": "text|bullet|image|chart|table",
      ...slot-specific fields...
    }
  }
}

Slot types and their required fields:
1. "text": {"slot_type": "text", "content": "Text content"}
2. "bullet": {"slot_type": "bullet", "items": ["Item 1", "Item 2", ...]} (3-7 items recommended)
3. "image": {"slot_type": "image", "alt_text": "Description of image"}
4. "chart": {"slot_type": "chart", "chart_type": "bar|line|pie|...", "data": {...}}
5. "table": {"slot_type": "table", "headers": ["Header1", ...], "rows": [["Cell1", ...], ...]}

Guidelines:
- Keep text concise and impactful
- Use bullet points for lists (3-7 items)
- Ensure content is relevant and accurate
- Match the tone and style requested
- For charts/tables, provide realistic sample data if needed
"""
    
    # Add slide-type-specific guidance
    if slide_type == SlideType.TITLE:
        return base_prompt + """
For TITLE slides:
- Use a single "title" text slot with the main presentation title
- Keep it short and memorable (5-10 words)
- Optionally add a subtitle in a second "subtitle" text slot
"""
    elif slide_type == SlideType.AGENDA:
        return base_prompt + """
For AGENDA slides:
- Use a "title" text slot: "Agenda" or "Contents"
- Use a "content" bullet slot with 5-8 agenda items
- Each item should be a clear section/topic
"""
    elif slide_type == SlideType.BULLET:
        return base_prompt + """
For BULLET slides:
- Use a "title" text slot for the slide topic
- Use a "content" bullet slot with 3-7 key points
- Each bullet should be concise (one line if possible)
- Use parallel structure
"""
    elif slide_type == SlideType.TWO_COLUMN:
        return base_prompt + """
For TWO_COLUMN slides:
- Use a "title" text slot for the slide topic
- Use "left" and "right" bullet slots (or text slots)
- Balance content between columns
- Each column should have 3-5 items
"""
    elif slide_type == SlideType.IMAGE:
        return base_prompt + """
For IMAGE slides:
- Use a "title" text slot for the slide topic
- Use an "image" slot with descriptive alt_text
- Optionally add a "caption" text slot below the image
"""
    elif slide_type == SlideType.CHART:
        return base_prompt + """
For CHART slides:
- Use a "title" text slot for the chart topic
- Use a "chart" slot with chart_type and data
- Provide realistic sample data in the data field
- Common chart types: bar, line, pie, area
"""
    elif slide_type == SlideType.TABLE:
        return base_prompt + """
For TABLE slides:
- Use a "title" text slot for the table topic
- Use a "table" slot with headers and rows
- Keep tables simple (3-5 columns, 3-7 rows)
- Provide realistic sample data
"""
    elif slide_type == SlideType.SECTION:
        return base_prompt + """
For SECTION slides:
- Use a "title" text slot for the section name
- Keep it simple and clear
- Optionally add a "subtitle" text slot
"""
    else:
        return base_prompt


def get_slide_builder_user_prompt(
    slide_plan,
    goal: Optional[str] = None,
    audience: Optional[str] = None,
    tone: Optional[str] = None
) -> str:
    """Get user prompt for slide builder"""
    prompt = f"""Generate content for a {slide_plan.slide_type.value} slide.

Slide Title: {slide_plan.title}
Slide Goal: {slide_plan.goal or goal or "Present information clearly"}
"""
    
    if audience:
        prompt += f"Target Audience: {audience}\n"
    if tone:
        prompt += f"Tone: {tone}\n"
    
    prompt += "\nGenerate high-quality, relevant content that matches the slide type and requirements. Return only valid JSON."
    
    return prompt


def get_slide_improvement_prompt(
    slide_plan,
    current_slide_ir,
    issues: list,
    reasoning: str = "",
    goal: Optional[str] = None,
    audience: Optional[str] = None,
    tone: Optional[str] = None
) -> str:
    """Get prompt for improving slide based on issues"""
    prompt = f"""Improve the following {slide_plan.slide_type.value} slide based on quality issues found.

Current Slide:
Title: {current_slide_ir.title}
Slots: {len(current_slide_ir.slots)} slots

Issues Found:
"""
    
    for issue in issues:
        prompt += f"- [{issue.get('severity', 'unknown')}] {issue.get('type', 'unknown')}: {issue.get('message', '')}\n"
    
    if reasoning:
        prompt += f"\nAnalysis: {reasoning}\n"
    
    prompt += f"""
Slide Goal: {slide_plan.goal or goal or "Present information clearly"}
"""
    
    if audience:
        prompt += f"Target Audience: {audience}\n"
    if tone:
        prompt += f"Tone: {tone}\n"
    
    prompt += """
IMPORTANT: You must fix the issues while maintaining or improving content quality:
- If overflow: Make text more concise, reduce bullet points, or restructure content
- If overlap: Adjust content structure to avoid overlapping elements
- If font too small: Ensure content fits with appropriate font sizes
- Keep content relevant, accurate, and impactful
- Maintain the slide's purpose and key messages

Return only valid JSON with the improved slide structure.
"""
    
    return prompt
