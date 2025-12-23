"""
Git Manager for MCP Servers

Handles GitHub repository cloning, pulling, and dependency installation.
"""

import os
import subprocess
import logging
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
import asyncio

logger = logging.getLogger(__name__)


class GitManager:
    """Manages Git operations for MCP server repositories."""
    
    def __init__(self, storage_path: str = "/data/mcp"):
        """Initialize Git Manager.
        
        Args:
            storage_path: Base path for storing MCP server repositories
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize repository name for filesystem.
        
        Args:
            name: Repository name or URL
            
        Returns:
            Sanitized name safe for filesystem
        """
        # Extract repo name from URL if needed
        if name.startswith("http"):
            name = name.rstrip("/").split("/")[-1]
            if name.endswith(".git"):
                name = name[:-4]
        
        # Replace invalid characters
        return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name)
    
    async def clone_or_pull(
        self,
        github_url: str,
        server_name: str,
        branch: Optional[str] = None
    ) -> Path:
        """Clone or pull GitHub repository.
        
        Args:
            github_url: GitHub repository URL
            server_name: Server name (used for directory name)
            branch: Branch to checkout (default: main/master)
            
        Returns:
            Path to cloned repository
            
        Raises:
            Exception: If clone/pull fails
        """
        repo_name = self._sanitize_name(server_name)
        repo_path = self.storage_path / repo_name
        
        # Clone if doesn't exist, pull if exists
        if not repo_path.exists():
            logger.info(f"Cloning repository: {github_url} to {repo_path}")
            await self._clone_repo(github_url, repo_path, branch)
        else:
            logger.info(f"Pulling repository: {repo_path}")
            await self._pull_repo(repo_path, branch)
        
        return repo_path
    
    async def _clone_repo(
        self,
        github_url: str,
        repo_path: Path,
        branch: Optional[str] = None
    ) -> None:
        """Clone repository.
        
        Args:
            github_url: Repository URL
            repo_path: Target path
            branch: Branch to checkout
        """
        cmd = ["git", "clone", github_url, str(repo_path)]
        if branch:
            cmd.extend(["-b", branch])
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise Exception(f"Failed to clone repository: {error_msg}")
        
        logger.info(f"Repository cloned successfully: {repo_path}")
    
    async def _pull_repo(
        self,
        repo_path: Path,
        branch: Optional[str] = None
    ) -> None:
        """Pull latest changes from repository.
        
        Args:
            repo_path: Repository path
            branch: Branch to pull
        """
        # Fetch latest changes
        fetch_cmd = ["git", "-C", str(repo_path), "fetch", "origin"]
        process = await asyncio.create_subprocess_exec(
            *fetch_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        
        # Reset to origin/branch or origin/main
        if branch:
            reset_cmd = ["git", "-C", str(repo_path), "reset", "--hard", f"origin/{branch}"]
        else:
            # Try main first, then master
            reset_cmd = ["git", "-C", str(repo_path), "reset", "--hard", "origin/main"]
        
        process = await asyncio.create_subprocess_exec(
            *reset_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            # Try master if main fails
            if not branch:
                reset_cmd = ["git", "-C", str(repo_path), "reset", "--hard", "origin/master"]
                process = await asyncio.create_subprocess_exec(
                    *reset_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
        
        logger.info(f"Repository pulled successfully: {repo_path}")
    
    async def install_dependencies(self, repo_path: Path) -> None:
        """Install dependencies for the repository.
        
        Detects and installs dependencies based on:
        - requirements.txt (Python)
        - package.json (Node.js)
        - pyproject.toml (Python)
        
        Args:
            repo_path: Repository path
        """
        # Check for Python dependencies
        if (repo_path / "requirements.txt").exists():
            await self._install_python_deps(repo_path)
        elif (repo_path / "pyproject.toml").exists():
            await self._install_python_deps(repo_path, use_poetry=True)
        
        # Check for Node.js dependencies
        if (repo_path / "package.json").exists():
            await self._install_node_deps(repo_path)
    
    async def _install_python_deps(
        self,
        repo_path: Path,
        use_poetry: bool = False
    ) -> None:
        """Install Python dependencies.
        
        Args:
            repo_path: Repository path
            use_poetry: Use Poetry if pyproject.toml exists
        """
        # Always create virtual environment if .venv doesn't exist
        venv_path = repo_path / ".venv"
        if not venv_path.exists():
            logger.info(f"Creating virtual environment: {venv_path}")
            create_venv = await asyncio.create_subprocess_exec(
                "python3", "-m", "venv", str(venv_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await create_venv.communicate()
            if create_venv.returncode != 0:
                raise Exception(f"Failed to create virtual environment: {venv_path}")
        
        # Get pip path from venv
        pip_path = venv_path / "bin" / "pip"
        if not pip_path.exists():
            pip_path = venv_path / "Scripts" / "pip.exe"  # Windows
        
        if use_poetry:
            # Check if poetry is available
            poetry_available = False
            try:
                check_poetry = await asyncio.create_subprocess_exec(
                    "poetry", "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await check_poetry.communicate()
                poetry_available = (check_poetry.returncode == 0)
            except (FileNotFoundError, OSError):
                # Poetry not available
                poetry_available = False
                logger.info("Poetry not available, using pip instead")
            
            if poetry_available:
                # Use poetry in venv
                poetry_path = venv_path / "bin" / "poetry"
                if not poetry_path.exists():
                    # Install poetry in venv
                    install_poetry = await asyncio.create_subprocess_exec(
                        str(pip_path), "install", "poetry",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await install_poetry.communicate()
                
                cmd = [str(venv_path / "bin" / "poetry"), "install", "--no-interaction"]
                cwd = str(repo_path)
            else:
                # Fallback to pip with pyproject.toml
                cmd = [str(pip_path), "install", "-e", "."]
                cwd = str(repo_path)
        else:
            # Install dependencies with requirements.txt
            cmd = [str(pip_path), "install", "-r", "requirements.txt"]
            cwd = str(repo_path)
        
        logger.info(f"Installing Python dependencies: {' '.join(cmd)}")
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            logger.warning(f"Failed to install Python dependencies: {error_msg}")
            # Don't raise - some repos might not need dependencies
        else:
            logger.info(f"Python dependencies installed successfully")
    
    async def _install_node_deps(self, repo_path: Path) -> None:
        """Install Node.js dependencies.
        
        Args:
            repo_path: Repository path
        """
        # Check if npm/yarn is available
        check_npm = await asyncio.create_subprocess_exec(
            "npm", "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await check_npm.communicate()
        
        if check_npm.returncode != 0:
            logger.warning("npm not available, skipping Node.js dependencies")
            return
        
        # Check for package-lock.json or yarn.lock
        if (repo_path / "yarn.lock").exists():
            cmd = ["yarn", "install"]
        else:
            cmd = ["npm", "install"]
        
        logger.info(f"Installing Node.js dependencies: {' '.join(cmd)}")
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(repo_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            logger.warning(f"Failed to install Node.js dependencies: {error_msg}")
        else:
            logger.info(f"Node.js dependencies installed successfully")
    
    def get_repo_path(self, server_name: str) -> Path:
        """Get repository path for a server.
        
        Args:
            server_name: Server name
            
        Returns:
            Repository path
        """
        repo_name = self._sanitize_name(server_name)
        return self.storage_path / repo_name
    
    def delete_repo(self, server_name: str) -> None:
        """Delete repository.
        
        Args:
            server_name: Server name
        """
        repo_path = self.get_repo_path(server_name)
        if repo_path.exists():
            shutil.rmtree(repo_path)
            logger.info(f"Repository deleted: {repo_path}")

