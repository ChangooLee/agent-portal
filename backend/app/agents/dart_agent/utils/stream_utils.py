# agent/utils/stream_utils.py
from typing import Any, Dict, Iterable, List, Tuple, Optional
from collections import defaultdict
import json


class StreamAccumulator:
    """
    LangGraph stream 이벤트 누적/조립기
    - messages: 토큰/툴콜/툴결과를 최종 메시지로 재조립
    - values/updates/custom/debug: 최근 값 보관(필요시 UI에 뿌리기)
    """

    def __init__(self) -> None:
        self.message_buffers: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
        self.last_values: Optional[Dict[str, Any]] = None
        self.last_updates: List[Dict[str, Any]] = []
        self.last_customs: List[Dict[str, Any]] = []
        self.last_debugs: List[Dict[str, Any]] = []

    @staticmethod
    def _path_key(path: List[str]) -> str:
        return "/".join(path or ["root"])

    def _msg_key(self, event: Dict[str, Any]) -> Tuple[str, str, str]:
        rid = event.get("metadata", {}).get("run_id", "run_unknown")
        path = self._path_key(event.get("subgraph_path", ["root"]))
        node = event.get("metadata", {}).get("langgraph_node", "node_unknown")
        return (rid, path, node)

    def feed(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        mode = event.get("mode")
        if mode == "values":
            self.last_values = event
            return None
        if mode == "updates":
            self.last_updates.append(event)
            return None
        if mode == "custom":
            self.last_customs.append(event)
            return None
        if mode == "debug":
            self.last_debugs.append(event)
            return None

        if mode == "messages":
            key = self._msg_key(event)
            chunk = event.get("message_chunk", {})
            self.message_buffers[key].append(chunk)
            fin = chunk.get("finish_reason")
            if fin in ("stop", "tool_call"):
                assembled = self._assemble_message(self.message_buffers[key])
                self.message_buffers[key].clear()
                return {
                    "run_id": key[0],
                    "subgraph_path": key[1],
                    "node": key[2],
                    "final_message": assembled,
                    "finish_reason": fin,
                    "metadata": event.get("metadata", {}),
                }
        return None

    def _assemble_message(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        text_parts: List[str] = []
        tool_calls: List[Dict[str, Any]] = []
        tool_results: List[Dict[str, Any]] = []
        current_tool: Optional[Dict[str, Any]] = None

        for ch in chunks:
            t = ch.get("type")
            if t == "chat_message_chunk":
                text_parts.append(ch.get("content", ""))

            elif t == "tool_call_chunk":
                call = ch.get("tool_call", {})
                if current_tool is None:
                    current_tool = {"name": call.get("name"), "arguments_str": ""}
                current_tool["arguments_str"] += call.get("arguments_delta", "")
                if ch.get("finish_reason") == "tool_call":
                    args_s = current_tool["arguments_str"]
                    try:
                        arguments = json.loads(args_s)
                        # raw_args가 있으면 개별 파라미터로 변환
                        if "raw_args" in arguments:
                            raw_args_str = arguments["raw_args"]
                            try:
                                raw_args = json.loads(raw_args_str)
                                arguments = raw_args
                            except Exception:
                                # raw_args 파싱 실패시 원본 유지
                                pass
                    except Exception:
                        arguments = {"$raw": args_s}
                    tool_calls.append({"name": current_tool["name"], "arguments": arguments})
                    current_tool = None

            elif t == "tool_result_message":
                tool_results.append({"name": ch.get("name"), "content": ch.get("content")})

        return {
            "text": "".join(text_parts).strip() or None,
            "tool_calls": tool_calls or None,
            "tool_results": tool_results or None,
        }