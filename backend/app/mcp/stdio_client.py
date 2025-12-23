"""
stdio MCP Client

Client for communicating with stdio-based MCP servers using the MCP SDK.
"""

import os
import asyncio
import logging
import platform
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.types import Tool
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("MCP SDK not available. Install with: pip install mcp")


class MCPStdioClient:
    """Client for stdio-based MCP servers."""
    
    def __init__(self, server_id: str):
        """Initialize stdio MCP client.
        
        Args:
            server_id: Server ID
        """
        if not MCP_AVAILABLE:
            raise ImportError("MCP SDK is not available. Install with: pip install mcp")
        
        self.server_id = server_id
        self.session: Optional[ClientSession] = None
        self._connection_params: Optional[StdioServerParameters] = None
        self._connected = False
        self._session_context: Optional[str] = None
    
    async def connect(
        self,
        command: str,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        reuse_existing_process: bool = True,
        existing_process: Optional[Any] = None
    ) -> List[Tool]:
        """Connect to stdio MCP server.
        
        Args:
            command: Command to execute (e.g., "/path/to/.venv/bin/mcp-opendart")
            cwd: Working directory
            env: Environment variables
            reuse_existing_process: If True, try to reuse existing process via HTTP adapter
            
        Returns:
            List of available tools
            
        Raises:
            Exception: If connection fails
        """
        if self._connected:
            logger.warning(f"Client {self.server_id} already connected")
            return await self.list_tools()
        
        # First, check if process is already running via process_manager
        from app.mcp.process_manager import process_manager
        running_process = process_manager.get_process(self.server_id)
        
        # Use provided existing_process if available, otherwise use running_process
        process_to_use = existing_process if existing_process is not None else running_process
        
        # If we have a running process and reuse_existing_process is True, use it
        if process_to_use is not None and reuse_existing_process:
            if process_to_use.returncode is not None:
                logger.warning(f"Process {self.server_id} has already exited (returncode: {process_to_use.returncode})")
                process_to_use = None
            else:
                # Process is running, use it
                try:
                    logger.info(f"[DEBUG] Connecting to existing process stdin/stdout for {self.server_id}")
                    logger.info(f"[DEBUG] Process: {process_to_use}, Returncode: {process_to_use.returncode}, PID: {process_to_use.pid if hasattr(process_to_use, 'pid') else 'N/A'}")
                    
                    # Get process stdin/stdout
                    process_stdin = process_to_use.stdin
                    process_stdout = process_to_use.stdout
                    
                    logger.info(f"[DEBUG] Process stdin: {process_stdin is not None}, stdout: {process_stdout is not None}")
                    
                    if process_stdin is None or process_stdout is None:
                        raise Exception("Process stdin/stdout not available")
                    
                    # Use manual JSON-RPC connection to existing process
                    logger.info("Using existing process streams for MCP communication via manual JSON-RPC")
                    return await self._connect_to_existing_process(process_stdin, process_stdout)
                    
                except Exception as e:
                    logger.warning(f"Failed to use existing process streams: {e}, starting new process")
                    process_to_use = None
        
        # If no running process, start a new one
        logger.info(f"Starting new stdio process for {self.server_id}")
        
        # Parse command
        cmd_parts = command.split()
        executable = cmd_parts[0]
        args = cmd_parts[1:] if len(cmd_parts) > 1 else []
        
        # Resolve executable path if relative
        if not os.path.isabs(executable) and cwd:
            executable = os.path.join(cwd, executable)
            if not os.path.exists(executable):
                # Try with .venv/bin prefix
                venv_executable = os.path.join(cwd, ".venv", "bin", os.path.basename(executable))
                if os.path.exists(venv_executable):
                    executable = venv_executable
        
        # Prepare environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        
        # Create stdio server parameters
        if platform.system() == "Windows":
            self._connection_params = StdioServerParameters(
                command="cmd",
                args=[
                    "/c",
                    f"{executable} {' '.join(args)} || echo Command failed with exit code %errorlevel% 1>&2",
                ],
                env=process_env,
            )
        else:
            # Use bash to execute command
            self._connection_params = StdioServerParameters(
                command="bash",
                args=["-c", f"exec {command} || echo 'Command failed with exit code $?' >&2"],
                env=process_env,
            )
        
        # Generate session context
        import uuid
        self._session_context = f"{self.server_id}_{uuid.uuid4().hex[:8]}"
        
        # Create session using stdio_client with timeout
        try:
            # stdio_client returns an async context manager
            # We need to enter it and keep it alive
            self._stdio_context = stdio_client(self._connection_params)
            
            # Enter the context manager (no timeout - agent mode)
            read, write = await self._stdio_context.__aenter__()
            
            # Create ClientSession with the streams
            self.session = ClientSession(read, write)
            
            # Initialize (no timeout - agent mode)
            await self.session.initialize()
            
            self._connected = True
            logger.info(f"Connected to stdio MCP server: {self.server_id}")
            
            # List tools (no timeout - agent mode)
            tools = await self.list_tools()
            
            # Store streams to keep connection alive
            self._read_stream = read
            self._write_stream = write
            
            return tools
                
        except Exception as e:
            logger.error(f"Failed to connect to stdio MCP server {self.server_id}: {e}", exc_info=True)
            self._connected = False
            if hasattr(self, '_stdio_context') and self._stdio_context:
                try:
                    await self._stdio_context.__aexit__(None, None, None)
                except:
                    pass
            raise
    
    async def list_tools(self) -> List[Tool]:
        """List available tools.
        
        Returns:
            List of tools
            
        Raises:
            Exception: If not connected
        """
        # If using manual connection, send tools/list request directly
        if hasattr(self, '_manual_connection') and self._manual_connection:
            import json
            import asyncio
            import uuid
            from app.mcp.process_manager import process_manager
            
            # Generate request ID
            request_id = int(uuid.uuid4().hex[:8], 16)
            
            tools_request = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/list"
            }
            
            tools_json = json.dumps(tools_request) + "\n"
            self._process_stdin.write(tools_json.encode())
            await self._process_stdin.drain()
            
            # Read response from stdout buffer (no timeout - agent mode)
            max_wait = 3600.0  # 1 hour (effectively unlimited for agent operations)
            wait_interval = 0.1
            waited = 0.0
            tools_line = None
            
            logger.debug(f"Waiting for tools/list response (id={request_id}) in stdout buffer...")
            while waited < max_wait:
                buffer = process_manager.get_stdout_buffer(self.server_id)
                for msg in buffer:
                    try:
                        msg_obj = json.loads(msg)
                        if msg_obj.get("id") == request_id and "result" in msg_obj:
                            tools_line = msg.encode('utf-8')
                            break
                    except:
                        continue
                
                if tools_line:
                    break
                
                await asyncio.sleep(wait_interval)
                waited += wait_interval
            
            if not tools_line:
                raise Exception("Tools/list timeout: MCP server did not respond")
            
            tools_response = json.loads(tools_line.decode('utf-8').strip())
            if "error" in tools_response:
                raise Exception(f"MCP tools/list error: {tools_response['error']}")
            
            # Convert to Tool objects
            tools_data = tools_response.get("result", {}).get("tools", [])
            tools = []
            for tool_data in tools_data:
                from mcp.types import Tool
                tool = Tool(
                    name=tool_data.get("name", ""),
                    description=tool_data.get("description", ""),
                    inputSchema=tool_data.get("inputSchema", {})
                )
                tools.append(tool)
            
            return tools
        
        # Use MCP SDK session
        if not self._connected or not self.session:
            raise Exception("Not connected to MCP server")
        
        try:
            response = await self.session.list_tools()
            return response.tools
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            raise
    
    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Any:
        """Call a tool.
        
        Args:
            tool_name: Tool name
            arguments: Tool arguments
            
        Returns:
            Tool result
            
        Raises:
            Exception: If not connected or tool call fails
        """
        if not self._connected:
            raise Exception("Not connected to MCP server")
        
        # If using manual connection, send tools/call request directly
        if hasattr(self, '_manual_connection') and self._manual_connection:
            import json
            import asyncio
            import uuid
            
            # Generate request ID
            request_id = int(uuid.uuid4().hex[:8], 16)
            
            # Send tools/call request
            call_request = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            call_json = json.dumps(call_request) + "\n"
            self._process_stdin.write(call_json.encode('utf-8'))
            await self._process_stdin.drain()
            
            logger.debug(f"Sent tools/call request for {tool_name}")
            
            # Read response from stdout buffer (no timeout - agent mode)
            from app.mcp.process_manager import process_manager
            
            max_wait = 3600.0  # 1 hour (effectively unlimited for agent operations)
            wait_interval = 0.1
            waited = 0.0
            response_line = None
            
            logger.debug(f"Waiting for tools/call response (id={request_id}) in stdout buffer...")
            while waited < max_wait:
                buffer = process_manager.get_stdout_buffer(self.server_id)
                for msg in buffer:
                    try:
                        msg_obj = json.loads(msg)
                        if msg_obj.get("id") == request_id and "result" in msg_obj:
                            # msg는 이미 문자열이므로 그대로 사용
                            response_line = msg
                            # 응답을 찾았으므로 버퍼에서 제거하지 않음 (다른 요청에서 재사용 가능)
                            break
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        logger.debug(f"Error parsing message: {e}")
                        continue
                
                if response_line:
                    break
                
                await asyncio.sleep(wait_interval)
                waited += wait_interval
            
            if not response_line:
                raise Exception(f"Tools/call timeout for {tool_name}")
            
            call_response = json.loads(response_line.strip())
            if "error" in call_response:
                error_detail = call_response.get("error", {})
                error_msg = error_detail.get("message", str(error_detail)) if isinstance(error_detail, dict) else str(error_detail)
                raise Exception(f"MCP tools/call error: {error_msg}")
            
            # Extract content from result
            result = call_response.get("result", {})
            content = result.get("content", [])
            
            # Convert content to list of text strings
            # Handle bytes objects by decoding them
            if isinstance(content, list):
                processed_content = []
                for item in content:
                    if isinstance(item, bytes):
                        processed_content.append(item.decode('utf-8', errors='replace'))
                    elif isinstance(item, dict):
                        # Handle dict items (e.g., {"type": "text", "text": "..."})
                        processed_item = item.copy()
                        if "text" in processed_item:
                            if isinstance(processed_item["text"], bytes):
                                processed_item["text"] = processed_item["text"].decode('utf-8', errors='replace')
                        processed_content.append(processed_item)
                    else:
                        processed_content.append(item)
                return processed_content
            else:
                if isinstance(content, bytes):
                    return [content.decode('utf-8', errors='replace')]
                return [content]
        
        # Use MCP SDK session
        if not self.session:
            raise Exception("Not connected to MCP server (no session)")
        
        try:
            response = await self.session.call_tool(tool_name, arguments)
            return response.content
        except Exception as e:
            logger.error(f"Failed to call tool {tool_name}: {e}")
            raise
    
    async def _connect_to_existing_process(
        self,
        process_stdin: Any,
        process_stdout: Any
    ) -> List[Tool]:
        """Connect to existing process using its stdin/stdout with manual JSON-RPC.
        
        Args:
            process_stdin: Process stdin pipe (asyncio StreamWriter)
            process_stdout: Process stdout pipe (asyncio StreamReader)
            
        Returns:
            List of tools
        """
        import json
        import uuid
        
        try:
            # Send initialize request
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "agent-portal",
                        "version": "1.0.0"
                    }
                }
            }
            
            # Write initialize request
            init_json = json.dumps(init_request) + "\n"
            process_stdin.write(init_json.encode())
            await process_stdin.drain()
            
            # Read initialize response (no timeout - agent mode)
            # Note: process_stdout은 process_manager의 _read_logs에서 읽고 있으므로
            # stdout 버퍼에서 JSON-RPC 메시지를 가져와야 합니다
            from app.mcp.process_manager import process_manager
            
            import asyncio
            max_wait = 3600.0  # 1 hour (effectively unlimited for agent operations)
            wait_interval = 0.1
            waited = 0.0
            response_line = None
            
            logger.info(f"[DEBUG] Waiting for initialize response in stdout buffer...")
            while waited < max_wait:
                # stdout 버퍼에서 JSON-RPC 메시지 찾기
                buffer = process_manager.get_stdout_buffers().get(self.server_id, [])
                logger.info(f"[DEBUG] Buffer size: {len(buffer)}, waited: {waited:.1f}s")
                if buffer:
                    logger.info(f"[DEBUG] Buffer contents (last 3): {buffer[-3:]}")
                
                for msg in buffer:
                    try:
                        msg_obj = json.loads(msg)
                        logger.info(f"[DEBUG] Checking message: id={msg_obj.get('id')}, has_result={'result' in msg_obj}")
                        if msg_obj.get("id") == 1 and "result" in msg_obj:
                            response_line = msg.encode('utf-8')
                            logger.info(f"[DEBUG] Found initialize response!")
                            break
                    except Exception as e:
                        logger.debug(f"[DEBUG] Failed to parse message: {e}")
                        continue
                
                if response_line:
                    break
                
                await asyncio.sleep(wait_interval)
                waited += wait_interval
            
            if not response_line:
                buffer = process_manager.get_stdout_buffers().get(self.server_id, [])
                logger.error(f"[DEBUG] Initialize timeout. Buffer size: {len(buffer)}, contents: {buffer[-5:]}")
                raise Exception("Initialize timeout: MCP server did not respond")
            
            init_response = json.loads(response_line.decode('utf-8').strip())
            if "error" in init_response:
                raise Exception(f"MCP initialize error: {init_response['error']}")
            
            # Send initialized notification
            initialized_notification = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }
            notif_json = json.dumps(initialized_notification) + "\n"
            process_stdin.write(notif_json.encode())
            await process_stdin.drain()
            
            # Send tools/list request
            tools_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list"
            }
            
            tools_json = json.dumps(tools_request) + "\n"
            process_stdin.write(tools_json.encode())
            await process_stdin.drain()
            
            # Read tools/list response (no timeout - agent mode)
            # stdout 버퍼에서 JSON-RPC 메시지 찾기
            logger.info(f"[DEBUG] Waiting for tools/list response in stdout buffer...")
            max_wait = 3600.0  # 1 hour (effectively unlimited for agent operations)
            wait_interval = 0.1
            waited = 0.0
            tools_line = None
            
            while waited < max_wait:
                # stdout 버퍼에서 JSON-RPC 메시지 찾기
                buffer = process_manager.get_stdout_buffers().get(self.server_id, [])
                logger.info(f"[DEBUG] Buffer size: {len(buffer)}, waited: {waited:.1f}s")
                
                for msg in buffer:
                    try:
                        msg_obj = json.loads(msg)
                        logger.info(f"[DEBUG] Checking message: id={msg_obj.get('id')}, has_result={'result' in msg_obj}")
                        if msg_obj.get("id") == 2 and "result" in msg_obj:
                            tools_line = msg.encode('utf-8')
                            logger.info(f"[DEBUG] Found tools/list response!")
                            break
                    except Exception as e:
                        logger.debug(f"[DEBUG] Failed to parse message: {e}")
                        continue
                
                if tools_line:
                    break
                
                await asyncio.sleep(wait_interval)
                waited += wait_interval
            
            if not tools_line:
                buffer = process_manager.get_stdout_buffers().get(self.server_id, [])
                logger.error(f"[DEBUG] Tools/list timeout. Buffer size: {len(buffer)}, contents: {buffer[-5:]}")
                raise Exception("Tools/list timeout: MCP server did not respond")
            
            tools_response = json.loads(tools_line.decode('utf-8').strip())
            if "error" in tools_response:
                raise Exception(f"MCP tools/list error: {tools_response['error']}")
            
            # Convert to Tool objects
            tools_data = tools_response.get("result", {}).get("tools", [])
            tools = []
            for tool_data in tools_data:
                from mcp.types import Tool
                tool = Tool(
                    name=tool_data.get("name", ""),
                    description=tool_data.get("description", ""),
                    inputSchema=tool_data.get("inputSchema", {})
                )
                tools.append(tool)
            
            # Mark as connected (but we're using manual communication)
            self._connected = True
            self._manual_connection = True
            self._process_stdin = process_stdin
            self._process_stdout = process_stdout
            
            logger.info(f"Connected to existing process via manual JSON-RPC: {self.server_id}")
            return tools
            
        except Exception as e:
            logger.error(f"Failed to connect to existing process: {e}", exc_info=True)
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from MCP server."""
        if hasattr(self, '_stdio_context') and self._stdio_context:
            try:
                await self._stdio_context.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error closing stdio context: {e}")
        
        self.session = None
        self._connected = False
        self._connection_params = None
        self._read_stream = None
        self._write_stream = None
        self._stdio_context = None
        self._stdio_manager = None
        logger.info(f"Disconnected from stdio MCP server: {self.server_id}")
    
    def is_connected(self) -> bool:
        """Check if connected.
        
        Returns:
            True if connected
        """
        return self._connected and self.session is not None
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

