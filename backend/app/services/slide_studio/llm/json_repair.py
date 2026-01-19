"""JSON Repair - Fix broken JSON from LLM"""
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def repair_json(text: str, max_attempts: int = 3) -> Optional[Any]:
    """
    Repair broken JSON from LLM output.
    
    Args:
        text: JSON string (possibly broken)
        max_attempts: Maximum repair attempts
        
    Returns:
        Parsed JSON object or None
    """
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try json-repair library if available
    try:
        import json_repair
        repaired = json_repair.repair_json(text)
        return json.loads(repaired)
    except ImportError:
        logger.warning("json-repair library not available, using basic repair")
    except Exception as e:
        logger.warning(f"json-repair failed: {e}")
    
    # Basic repair: try to extract JSON from markdown code blocks
    import re
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try to find JSON object in text
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    
    return None


def parse_with_retry(
    text: str,
    schema_class,
    max_attempts: int = 3
) -> Optional[Any]:
    """
    Parse JSON with retry and schema validation.
    
    Args:
        text: JSON string
        schema_class: Pydantic model class
        max_attempts: Maximum retry attempts
        
    Returns:
        Parsed Pydantic model or None
    """
    for attempt in range(max_attempts):
        # Try to repair and parse
        parsed_json = repair_json(text)
        if parsed_json is None:
            continue
        
        # Try to validate with Pydantic
        try:
            return schema_class(**parsed_json)
        except Exception as e:
            logger.warning(f"Schema validation failed (attempt {attempt + 1}): {e}")
            if attempt == max_attempts - 1:
                return None
    
    return None
