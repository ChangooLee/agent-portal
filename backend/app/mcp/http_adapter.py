"""
HTTP Adapter for stdio MCP Servers

Wraps stdio MCP servers with HTTP endpoints for Kong Gateway integration.
"""

import asyncio
import logging
import json
from typing import Dict, Any, Optional
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse

from .stdio_client import MCPStdioClient

logger = logging.getLogger(__name__)


class HTTPAdapter:
    """HTTP adapter for stdio MCP servers."""
    
    def __init__(self):
        """Initialize HTTP adapter."""
        self.clients: Dict[str, MCPStdioClient] = {}
        self._client_locks: Dict[str, asyncio.Lock] = {}
    
    async def get_client(self, server_id: str) -> MCPStdioClient:
        """Get or create MCP client for server.
        
        Args:
            server_id: Server ID
            
        Returns:
            MCP client
            
        Raises:
            HTTPException: If client creation fails
        """
        if server_id not in self.clients:
            # Create lock for this server
            if server_id not in self._client_locks:
                self._client_locks[server_id] = asyncio.Lock()
            
            async with self._client_locks[server_id]:
                # Double-check after acquiring lock
                if server_id not in self.clients:
                    self.clients[server_id] = MCPStdioClient(server_id)
        
        return self.clients[server_id]
    
    async def handle_request(
        self,
        server_id: str,
        request: Request,
        command: str,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None
    ) -> Response:
        """Handle HTTP request and route to stdio MCP server.
        
        Args:
            server_id: Server ID
            request: FastAPI request
            command: MCP server command
            cwd: Working directory
            env: Environment variables
            
        Returns:
            HTTP response
        """
        try:
            # Parse request body
            body = await request.body()
            if body:
                try:
                    payload = json.loads(body)
                except json.JSONDecodeError:
                    payload = {}
            else:
                payload = {}
            
            # Get client
            client = await self.get_client(server_id)
            
            # Connect if not connected
            # For stdio MCP, we need to connect to the existing process, not start a new one
            if not client.is_connected():
                # Check if process is already running via ProcessManager
                from app.mcp.process_manager import process_manager
                existing_process = process_manager.get_process(server_id)
                
                if existing_process and existing_process.returncode is None:
                    # Process is already running, connect to it
                    # Note: stdio_client will start a new process, so we need a different approach
                    # For now, we'll still use connect but it should reuse if possible
                    logger.info(f"Process {server_id} already running, connecting to it")
                
                await client.connect(command, cwd, env, reuse_existing_process=True)
            
            # Route request based on path
            path = request.url.path
            method = request.method
            
            if path.endswith("/tools/list") or "tools/list" in path:
                # List tools
                tools = await client.list_tools()
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": payload.get("id"),
                    "result": {
                        "tools": [
                            {
                                "name": tool.name,
                                "description": tool.description,
                                "inputSchema": tool.inputSchema
                            }
                            for tool in tools
                        ]
                    }
                })
            
            elif path.endswith("/tools/call") or "tools/call" in path:
                # Call tool
                tool_name = payload.get("name") or payload.get("tool_name")
                arguments = payload.get("arguments") or payload.get("params", {}).get("arguments", {})
                
                if not tool_name:
                    raise HTTPException(status_code=400, detail="tool_name is required")
                
                result = await client.call_tool(tool_name, arguments)
                
                # Format result
                if isinstance(result, list):
                    # MCP returns list of content items
                    formatted_result = []
                    for item in result:
                        if hasattr(item, 'text'):
                            formatted_result.append({"type": "text", "text": item.text})
                        elif hasattr(item, 'content'):
                            formatted_result.append({"type": "text", "text": str(item.content)})
                        else:
                            formatted_result.append({"type": "text", "text": str(item)})
                else:
                    formatted_result = [{"type": "text", "text": str(result)}]
                
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": payload.get("id"),
                    "result": {
                        "content": formatted_result
                    }
                })
            
            elif path.endswith("/initialize") or "initialize" in path:
                # Initialize (already done in connect)
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": payload.get("id"),
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "serverInfo": {
                            "name": server_id,
                            "version": "1.0.0"
                        }
                    }
                })
            
            else:
                # Generic JSON-RPC handling
                rpc_method = payload.get("method", "")
                
                if rpc_method == "tools/list":
                    tools = await client.list_tools()
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": payload.get("id"),
                        "result": {
                            "tools": [
                                {
                                    "name": tool.name,
                                    "description": tool.description,
                                    "inputSchema": tool.inputSchema
                                }
                                for tool in tools
                            ]
                        }
                    })
                
                elif rpc_method == "tools/call":
                    tool_name = payload.get("params", {}).get("name")
                    arguments = payload.get("params", {}).get("arguments", {})
                    
                    if not tool_name:
                        raise HTTPException(status_code=400, detail="tool_name is required")
                    
                    result = await client.call_tool(tool_name, arguments)
                    
                    # Format result
                    if isinstance(result, list):
                        formatted_result = []
                        for item in result:
                            if hasattr(item, 'text'):
                                formatted_result.append({"type": "text", "text": item.text})
                            elif hasattr(item, 'content'):
                                formatted_result.append({"type": "text", "text": str(item.content)})
                            else:
                                formatted_result.append({"type": "text", "text": str(item)})
                    else:
                        formatted_result = [{"type": "text", "text": str(result)}]
                    
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": payload.get("id"),
                        "result": {
                            "content": formatted_result
                        }
                    })
                
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Unknown method: {rpc_method}"
                    )
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error handling request for {server_id}: {e}", exc_info=True)
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "id": payload.get("id") if 'payload' in locals() else None,
                    "error": {
                        "code": -32000,
                        "message": str(e)
                    }
                },
                status_code=500
            )
    
    async def disconnect_client(self, server_id: str) -> None:
        """Disconnect client for server.
        
        Args:
            server_id: Server ID
        """
        if server_id in self.clients:
            try:
                await self.clients[server_id].disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting client {server_id}: {e}")
            finally:
                del self.clients[server_id]
        
        if server_id in self._client_locks:
            del self._client_locks[server_id]
    
    async def cleanup(self, server_id: str) -> None:
        """Cleanup adapter resources.
        
        Args:
            server_id: Server ID
        """
        await self.disconnect_client(server_id)


# Singleton instance
http_adapter = HTTPAdapter()

