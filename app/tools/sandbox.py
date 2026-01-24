"""
Production-Grade Docker Sandbox for Secure Code Execution
Supports file injection for handling imports and dependencies
"""

import docker
from docker.errors import DockerException, ContainerError, ImageNotFound
from typing import Dict, Optional, Tuple
import tempfile
import tarfile
import io
import logging
from pathlib import Path
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class SandboxError(Exception):
    """Base exception for sandbox-related errors"""
    pass


class SandboxTimeoutError(SandboxError):
    """Raised when sandbox execution times out"""
    pass


class DockerSandbox:
    """
    Production-grade Docker sandbox with file injection support
    
    Features:
    - File dictionary support for handling imports
    - Network isolation by default
    - Memory limits
    - Automatic cleanup
    - Comprehensive error handling
    """
    
    def __init__(
        self,
        image: Optional[str] = None,
        memory_limit: Optional[str] = None,
        network_disabled: Optional[bool] = None,
        working_dir: str = "/workspace"
    ):
        """
        Initialize Docker sandbox
        
        Args:
            image: Docker image to use (defaults to config)
            memory_limit: Memory limit (e.g., "512m")
            network_disabled: Whether to disable network access
            working_dir: Working directory inside container
        """
        settings = get_settings()
        
        self.image = image or settings.docker_image
        self.memory_limit = memory_limit or settings.docker_memory_limit
        self.network_disabled = network_disabled if network_disabled is not None else settings.docker_network_disabled
        self.working_dir = working_dir
        
        try:
            self.client = docker.from_env()
            logger.info(f"Docker client initialized with image: {self.image}")
        except DockerException as e:
            raise SandboxError(f"Failed to initialize Docker client: {e}") from e
        
        self._ensure_image_available()
    
    def _ensure_image_available(self):
        """Ensure the Docker image is available locally"""
        try:
            self.client.images.get(self.image)
            logger.debug(f"Docker image {self.image} found locally")
        except ImageNotFound:
            logger.info(f"Docker image {self.image} not found, pulling...")
            try:
                self.client.images.pull(self.image)
                logger.info(f"Successfully pulled image: {self.image}")
            except DockerException as e:
                raise SandboxError(f"Failed to pull Docker image {self.image}: {e}") from e
    
    def _create_tar_archive(self, files: Dict[str, str]) -> bytes:
        """
        Create a tar archive from file dictionary
        
        Args:
            files: Dictionary mapping filenames to content
            
        Returns:
            bytes: Tar archive as bytes
        """
        tar_stream = io.BytesIO()
        tar = tarfile.open(fileobj=tar_stream, mode='w')
        
        for filename, content in files.items():
            # Convert content to bytes
            content_bytes = content.encode('utf-8')
            
            # Debug: Log what we're adding
            logger.info(f"[TAR] Adding {filename}: {len(content_bytes)} bytes")
            logger.info(f"[TAR]   First 100 bytes: {content_bytes[:100]!r}")
            
            # Create tarinfo
            tarinfo = tarfile.TarInfo(name=filename)
            tarinfo.size = len(content_bytes)
            tarinfo.mode = 0o644
            
            # Add to tar
            tar.addfile(tarinfo, io.BytesIO(content_bytes))
        
        tar.close()
        tar_stream.seek(0)
        return tar_stream.read()
    
    def run_in_context(
        self,
        command: str,
        files: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None
    ) -> Tuple[str, str, int]:
        """
        Run command in Docker container with file injection support
        
        Args:
            command: Command to execute (e.g., "python main.py")
            files: Dictionary of files to inject {'filename.py': 'content'}
            timeout: Execution timeout in seconds
            
        Returns:
            Tuple[str, str, int]: (stdout, stderr, exit_code)
            
        Raises:
            SandboxError: If execution fails
            SandboxTimeoutError: If execution times out
        """
        settings = get_settings()
        timeout = timeout or settings.docker_timeout
        files = files or {}
        
        container = None
        
        try:
            # Create container
            logger.debug(f"Creating container with image: {self.image}")
            
            container = self.client.containers.create(
                image=self.image,
                command=["sh", "-c", f"sleep {timeout + 5}"],  # Keep container alive
                working_dir=self.working_dir,
                mem_limit=self.memory_limit,
                network_disabled=self.network_disabled,
                detach=True
            )
            
            logger.debug(f"Container created: {container.id[:12]}")
            
            # Start container
            container.start()
            logger.debug(f"Container started: {container.id[:12]}")
            
            # Inject files if provided
            if files:
                logger.debug(f"Injecting {len(files)} files into container")
                tar_archive = self._create_tar_archive(files)
                container.put_archive(path=self.working_dir, data=tar_archive)
                logger.debug("Files injected successfully")
                
                # Debug: Verify the files were written correctly
                for fname in files.keys():
                    verify_result = container.exec_run(
                        cmd=["sh", "-c", f"cat {fname} | head -5"],
                        workdir=self.working_dir
                    )
                    logger.info(f"[VERIFY] {fname} first 5 lines: {verify_result.output.decode('utf-8', errors='ignore')[:300]!r}")
            
            # Execute command
            logger.info(f"Executing command: {command}")
            exec_result = container.exec_run(
                cmd=["sh", "-c", command],
                workdir=self.working_dir,
                demux=True,  # Separate stdout and stderr
                stdout=True,
                stderr=True
            )
            
            exit_code = exec_result.exit_code
            stdout_bytes, stderr_bytes = exec_result.output
            
            # Decode output
            stdout = stdout_bytes.decode('utf-8') if stdout_bytes else ""
            stderr = stderr_bytes.decode('utf-8') if stderr_bytes else ""
            
            logger.info(f"Command completed with exit code: {exit_code}")
            
            return stdout, stderr, exit_code
            
        except ContainerError as e:
            logger.error(f"Container error: {e}")
            raise SandboxError(f"Container execution failed: {e}") from e
        
        except Exception as e:
            logger.error(f"Unexpected error during execution: {e}")
            raise SandboxError(f"Sandbox execution failed: {e}") from e
        
        finally:
            # Cleanup container
            if container:
                try:
                    container.stop(timeout=1)
                    container.remove(force=True)
                    logger.debug(f"Container {container.id[:12]} cleaned up")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup container: {cleanup_error}")
    
    def run_python(
        self,
        code: str,
        dependencies: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None
    ) -> Tuple[str, str, int]:
        """
        Convenience method to run Python code
        
        Args:
            code: Python code to execute
            dependencies: Optional dependency files
            timeout: Execution timeout
            
        Returns:
            Tuple[str, str, int]: (stdout, stderr, exit_code)
        """
        files = {"main.py": code}
        if dependencies:
            files.update(dependencies)
        
        return self.run_in_context(
            command="python main.py",
            files=files,
            timeout=timeout
        )
    
    def health_check(self) -> bool:
        """
        Check if Docker daemon is accessible and image is available
        
        Returns:
            bool: True if healthy
        """
        try:
            self.client.ping()
            self._ensure_image_available()
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


def create_sandbox(**kwargs) -> DockerSandbox:
    """
    Factory function to create a DockerSandbox instance
    
    Args:
        **kwargs: Arguments to pass to DockerSandbox
        
    Returns:
        DockerSandbox: Configured sandbox instance
    """
    return DockerSandbox(**kwargs)
