"""
Stream utilities for safe async generator handling
"""
import json
import logging
from typing import AsyncGenerator, Dict, Any, Optional

logger = logging.getLogger(__name__)


async def safe_async_generator(
    gen: AsyncGenerator[Dict[str, Any], None],
    error_handler: Optional[callable] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    안전한 async generator 래퍼 - 예외 발생 시 정리 보장
    
    Args:
        gen: 원본 async generator
        error_handler: 예외 발생 시 호출할 핸들러 함수 (선택사항)
        
    Yields:
        원본 generator의 이벤트들
    """
    try:
        async for item in gen:
            yield item
    except Exception as e:
        logger.error(f"Error in async generator: {e}", exc_info=True)
        if error_handler:
            try:
                error_result = error_handler(e)
                if error_result:
                    yield error_result
            except Exception as handler_error:
                logger.error(f"Error handler failed: {handler_error}")
        else:
            # 기본 에러 이벤트 yield
            try:
                yield {
                    "event": "error",
                    "error": str(e)
                }
            except Exception as yield_error:
                logger.error(f"Failed to yield error event: {yield_error}")
    finally:
        # generator 정리 시도
        try:
            await gen.aclose()
        except Exception:
            # 이미 정리된 경우 무시
            pass


def create_error_response(error_message: str, code: str = "R40008") -> Dict[str, Any]:
    """에러 응답 생성"""
    return {
        "content": error_message,
        "event": "EXCEPTION",
        "status": "FAIL",
        "code": code,
        "error": error_message
    }

