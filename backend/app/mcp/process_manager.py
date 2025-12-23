"""
Process Manager for stdio MCP Servers

Manages the lifecycle of stdio-based MCP server processes.
"""

import os
import asyncio
import logging
import signal
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum
import json

logger = logging.getLogger(__name__)


class ProcessStatus(Enum):
    """Process status enumeration."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"


class ProcessManager:
    """Manages stdio MCP server processes."""
    
    def __init__(self):
        """Initialize Process Manager."""
        self.processes: Dict[str, asyncio.subprocess.Process] = {}
        self.process_status: Dict[str, ProcessStatus] = {}
        self.process_logs: Dict[str, List[str]] = {}
        self._stdout_buffers: Dict[str, List[str]] = {}  # JSON-RPC 메시지 버퍼
        self.max_log_lines = 1000
    
    async def start_process(
        self,
        server_id: str,
        command: str,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ) -> int:
        """Start stdio MCP server process.
        
        Args:
            server_id: Server ID
            command: Command to execute (e.g., "/path/to/.venv/bin/mcp-opendart")
            cwd: Working directory
            env: Environment variables
            timeout: Startup timeout in seconds
            
        Returns:
            Process PID
            
        Raises:
            Exception: If process fails to start
        """
        if server_id in self.processes:
            existing = self.processes[server_id]
            if existing.returncode is None:
                logger.warning(f"Process {server_id} already running")
                return existing.pid
        
        self.process_status[server_id] = ProcessStatus.STARTING
        self.process_logs[server_id] = []
        
        # Prepare environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        
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
        
        logger.info(f"Starting process {server_id}: {executable} {' '.join(args)}")
        
        try:
            # Start process
            process = await asyncio.create_subprocess_exec(
                executable,
                *args,
                cwd=cwd,
                env=process_env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,  # Merge stderr to stdout
                stdin=asyncio.subprocess.PIPE
            )
            
            self.processes[server_id] = process
            self.process_status[server_id] = ProcessStatus.RUNNING
            
            # Increase readline buffer limit for large MCP responses (10MB)
            if process.stdout and hasattr(process.stdout, '_limit'):
                process.stdout._limit = 1024 * 1024 * 10  # 10MB limit
                logger.info(f"Increased stdout buffer limit to 10MB for {server_id}")
            
            # Start log reader
            asyncio.create_task(self._read_logs(server_id, process))
            
            # Wait a bit to check if process started successfully
            await asyncio.sleep(1)
            
            if process.returncode is not None:
                # Process exited immediately
                error_msg = f"Process exited with code {process.returncode}"
                self.process_status[server_id] = ProcessStatus.ERROR
                raise Exception(error_msg)
            
            logger.info(f"Process {server_id} started successfully (PID: {process.pid})")
            return process.pid
            
        except Exception as e:
            self.process_status[server_id] = ProcessStatus.ERROR
            logger.error(f"Failed to start process {server_id}: {e}")
            raise
    
    async def _read_logs(
        self,
        server_id: str,
        process: asyncio.subprocess.Process
    ) -> None:
        """Read process logs asynchronously.
        
        stdout에서 읽은 내용을 버퍼에 저장하고, JSON-RPC 메시지인지 확인합니다.
        JSON-RPC 메시지가 아니면 로그로 저장합니다.
        
        Args:
            server_id: Server ID
            process: Process object
        """
        if server_id not in self.process_logs:
            self.process_logs[server_id] = []
        
        # stdout 버퍼 (JSON-RPC 메시지와 로그를 구분하기 위해)
        if not hasattr(self, '_stdout_buffers'):
            self._stdout_buffers = {}
        if server_id not in self._stdout_buffers:
            self._stdout_buffers[server_id] = []
        
        try:
            import json
            while True:
                if process.stdout is None:
                    break
                
                line = await process.stdout.readline()
                if not line:
                    break
                
                line_text = line.decode('utf-8', errors='replace').rstrip()
                
                # JSON-RPC 메시지인지 확인 ({"jsonrpc": "2.0"로 시작)
                try:
                    if line_text.strip().startswith('{') and '"jsonrpc"' in line_text:
                        # JSON-RPC 메시지 - 버퍼에 저장 (MCP 통신용)
                        logger.debug(f"[DEBUG] Found JSON-RPC message for {server_id}: {line_text[:100]}")
                        self._stdout_buffers[server_id].append(line_text)
                        # 버퍼 크기 제한 없음 (에이전트용)
                    else:
                        # 일반 로그
                        self._add_log(server_id, line_text)
                except Exception as e:
                    # 파싱 실패 시 일반 로그로 처리
                    logger.debug(f"[DEBUG] Failed to check JSON-RPC: {e}")
                    self._add_log(server_id, line_text)
                
                # Check if process exited
                if process.returncode is not None:
                    break
                    
        except Exception as e:
            logger.error(f"Error reading logs for {server_id}: {e}")
        finally:
            # Process exited
            if server_id in self.process_status:
                if self.process_status[server_id] == ProcessStatus.RUNNING:
                    self.process_status[server_id] = ProcessStatus.STOPPED
            logger.info(f"Process {server_id} log reader stopped")
    
    def get_stdout_buffers(self) -> Dict[str, List[str]]:
        """Get stdout buffers for all servers.
        
        Returns:
            Dictionary of server_id -> list of JSON-RPC messages
        """
        return self._stdout_buffers
    
    def get_stdout_buffer(self, server_id: str) -> List[str]:
        """Get stdout buffer for JSON-RPC messages.
        
        Args:
            server_id: Server ID
            
        Returns:
            List of JSON-RPC messages
        """
        return self._stdout_buffers.get(server_id, [])
    
    def clear_stdout_buffer(self, server_id: str) -> None:
        """Clear stdout buffer.
        
        Args:
            server_id: Server ID
        """
        if server_id in self._stdout_buffers:
            self._stdout_buffers[server_id] = []
    
    def _add_log(self, server_id: str, log_line: str) -> None:
        """Add log line to buffer.
        
        Args:
            server_id: Server ID
            log_line: Log line
        """
        if server_id not in self.process_logs:
            self.process_logs[server_id] = []
        
        self.process_logs[server_id].append(log_line)
        
        # Keep only last max_log_lines
        if len(self.process_logs[server_id]) > self.max_log_lines:
            self.process_logs[server_id] = self.process_logs[server_id][-self.max_log_lines:]
    
    async def stop_process(self, server_id: str, timeout: int = 10) -> bool:
        """Stop stdio MCP server process.
        
        Args:
            server_id: Server ID
            timeout: Graceful shutdown timeout
            
        Returns:
            True if stopped successfully
        """
        if server_id not in self.processes:
            logger.warning(f"Process {server_id} not found")
            return False
        
        process = self.processes[server_id]
        
        if process.returncode is not None:
            # Already stopped
            self.process_status[server_id] = ProcessStatus.STOPPED
            del self.processes[server_id]
            return True
        
        logger.info(f"Stopping process {server_id} (PID: {process.pid})")
        
        try:
            # Try graceful shutdown
            process.terminate()
            
            try:
                await asyncio.wait_for(process.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                # Force kill if graceful shutdown failed
                logger.warning(f"Process {server_id} did not terminate gracefully, killing")
                process.kill()
                await process.wait()
            
            self.process_status[server_id] = ProcessStatus.STOPPED
            del self.processes[server_id]
            
            logger.info(f"Process {server_id} stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping process {server_id}: {e}")
            self.process_status[server_id] = ProcessStatus.ERROR
            return False
    
    async def restart_process(
        self,
        server_id: str,
        command: str,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None
    ) -> int:
        """Restart stdio MCP server process.
        
        Args:
            server_id: Server ID
            command: Command to execute
            cwd: Working directory
            env: Environment variables
            
        Returns:
            New process PID
        """
        await self.stop_process(server_id)
        await asyncio.sleep(1)  # Brief pause before restart
        return await self.start_process(server_id, command, cwd, env)
    
    def get_process_status(self, server_id: str) -> ProcessStatus:
        """Get process status.
        
        Args:
            server_id: Server ID
            
        Returns:
            Process status
        """
        if server_id not in self.process_status:
            return ProcessStatus.STOPPED
        
        # Check if process is still running
        if server_id in self.processes:
            process = self.processes[server_id]
            if process.returncode is not None:
                # Process exited
                self.process_status[server_id] = ProcessStatus.STOPPED
                del self.processes[server_id]
        
        return self.process_status.get(server_id, ProcessStatus.STOPPED)
    
    def get_process_pid(self, server_id: str) -> Optional[int]:
        """Get process PID.
        
        Args:
            server_id: Server ID
            
        Returns:
            Process PID or None
        """
        if server_id in self.processes:
            process = self.processes[server_id]
            if process.returncode is None:
                return process.pid
        return None
    
    def get_logs(
        self,
        server_id: str,
        lines: Optional[int] = None
    ) -> List[str]:
        """Get process logs.
        
        Args:
            server_id: Server ID
            lines: Number of lines to return (default: all)
            
        Returns:
            List of log lines
        """
        if server_id not in self.process_logs:
            return []
        
        logs = self.process_logs[server_id]
        if lines:
            return logs[-lines:]
        return logs
    
    def get_process(self, server_id: str) -> Optional[asyncio.subprocess.Process]:
        """Get process object.
        
        Args:
            server_id: Server ID
            
        Returns:
            Process object or None
        """
        return self.processes.get(server_id)
    
    async def cleanup(self, server_id: str) -> None:
        """Cleanup process resources.
        
        Args:
            server_id: Server ID
        """
        await self.stop_process(server_id)
        if server_id in self.process_logs:
            del self.process_logs[server_id]
        if server_id in self.process_status:
            del self.process_status[server_id]


# Singleton instance
process_manager = ProcessManager()

