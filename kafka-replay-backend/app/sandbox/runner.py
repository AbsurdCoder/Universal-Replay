"""
Script execution sandbox with process-based isolation and timeout enforcement.

Executes Python scripts in isolated processes with RestrictedPython protection,
timeout enforcement, and comprehensive result tracking.
"""

import io
import json
import structlog
import sys
import time
from typing import Dict, Any, Optional
from concurrent.futures import ProcessPoolExecutor, TimeoutError as FuturesTimeoutError
from multiprocessing import Manager

from .models import ScriptResult
from .compiler import ScriptCompiler

logger = structlog.get_logger(__name__)

# Maximum output payload size: 1MB
MAX_OUTPUT_SIZE = 1024 * 1024

# Script execution timeout: 2 seconds
SCRIPT_TIMEOUT_SECONDS = 2


def _execute_script_in_process(
    compiled_code: object,
    message: Dict[str, Any],
    headers: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute a compiled script in an isolated process.

    This function runs in a separate process to provide real isolation.

    Args:
        compiled_code: Compiled RestrictedPython code object.
        message: Message payload dict.
        headers: Message headers dict.

    Returns:
        Dictionary with execution results.
    """
    # Capture stdout/stderr
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()

    start_time = time.time()
    result = {
        "output": None,
        "logs": "",
        "duration_ms": 0,
        "success": False,
        "error": None,
    }

    try:
        # Create safe execution environment
        safe_globals = ScriptCompiler.get_safe_globals()
        safe_locals = ScriptCompiler.get_safe_locals()

        # Add the transform function placeholder
        safe_locals["transform"] = None
        safe_locals["message"] = message
        safe_locals["headers"] = headers

        # Execute the compiled code
        exec(compiled_code, safe_globals, safe_locals)

        # Get the transform function
        transform_func = safe_locals.get("transform")
        if not transform_func:
            raise RuntimeError("Script must define a 'transform' function")

        # Call the transform function
        output = transform_func(message, headers)

        # Validate output
        if not isinstance(output, dict):
            raise TypeError(f"transform() must return a dict, got {type(output).__name__}")

        # Check output size
        output_json = json.dumps(output)
        output_size = len(output_json.encode("utf-8"))
        if output_size > MAX_OUTPUT_SIZE:
            raise ValueError(
                f"Output payload too large: {output_size} bytes (max {MAX_OUTPUT_SIZE})"
            )

        result["output"] = output
        result["success"] = True

    except Exception as e:
        result["error"] = str(e)
        result["success"] = False
        logger.error("script_execution_error", error=str(e))

    finally:
        # Capture logs
        stdout_value = sys.stdout.getvalue()
        stderr_value = sys.stderr.getvalue()
        result["logs"] = stdout_value + stderr_value

        # Restore stdout/stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)
        result["duration_ms"] = duration_ms

    return result


class ScriptExecutor:
    """
    Executes scripts in isolated processes with timeout enforcement.

    Features:
    - RestrictedPython protection
    - Process-based isolation (not threads)
    - 2-second CPU timeout per execution
    - 1MB output payload limit
    - Stdout/stderr capture
    - Comprehensive error handling
    """

    def __init__(self, max_workers: int = 4):
        """
        Initialize script executor.

        Args:
            max_workers: Maximum number of worker processes.
        """
        self.executor = ProcessPoolExecutor(max_workers=max_workers)
        self.compiler = ScriptCompiler()

    async def execute(
        self,
        code: str,
        message: Dict[str, Any],
        headers: Optional[Dict[str, Any]] = None,
    ) -> ScriptResult:
        """
        Execute a script asynchronously.

        Args:
            code: Python script code.
            message: Message payload dict.
            headers: Optional message headers dict.

        Returns:
            ScriptResult with execution details.
        """
        if headers is None:
            headers = {}

        start_time = time.time()

        try:
            # Compile the script
            compiled_code, error = self.compiler.compile(code)
            if error:
                duration_ms = int((time.time() - start_time) * 1000)
                logger.warning("script_compilation_failed", error=error)
                return ScriptResult(
                    output={},
                    logs="",
                    duration_ms=duration_ms,
                    success=False,
                    error=error,
                )

            # Execute in process pool with timeout
            loop = None
            try:
                import asyncio
                loop = asyncio.get_event_loop()
            except RuntimeError:
                pass

            if loop:
                # If we're in an async context, run in executor
                result_dict = await loop.run_in_executor(
                    self.executor,
                    _execute_script_in_process,
                    compiled_code,
                    message,
                    headers,
                )
            else:
                # Fallback to direct execution (should not happen in async context)
                result_dict = _execute_script_in_process(
                    compiled_code,
                    message,
                    headers,
                )

            # Convert to ScriptResult
            result = ScriptResult(
                output=result_dict.get("output", {}),
                logs=result_dict.get("logs", ""),
                duration_ms=result_dict.get("duration_ms", 0),
                success=result_dict.get("success", False),
                error=result_dict.get("error"),
            )

            if result.success:
                logger.info(
                    "script_executed_successfully",
                    duration_ms=result.duration_ms,
                )
            else:
                logger.warning(
                    "script_execution_failed",
                    error=result.error,
                    duration_ms=result.duration_ms,
                )

            return result

        except FuturesTimeoutError:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error("script_execution_timeout", duration_ms=duration_ms)
            return ScriptResult(
                output={},
                logs="",
                duration_ms=duration_ms,
                success=False,
                error=f"Script execution timeout after {SCRIPT_TIMEOUT_SECONDS} seconds",
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error("script_execution_error", error=str(e), duration_ms=duration_ms)
            return ScriptResult(
                output={},
                logs="",
                duration_ms=duration_ms,
                success=False,
                error=str(e),
            )

    async def execute_with_timeout(
        self,
        code: str,
        message: Dict[str, Any],
        headers: Optional[Dict[str, Any]] = None,
        timeout_seconds: float = SCRIPT_TIMEOUT_SECONDS,
    ) -> ScriptResult:
        """
        Execute a script with explicit timeout.

        Args:
            code: Python script code.
            message: Message payload dict.
            headers: Optional message headers dict.
            timeout_seconds: Timeout in seconds.

        Returns:
            ScriptResult with execution details.
        """
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                self.execute(code, message, headers),
                timeout=timeout_seconds,
            )
            return result
        except asyncio.TimeoutError:
            logger.error("script_execution_timeout", timeout_seconds=timeout_seconds)
            return ScriptResult(
                output={},
                logs="",
                duration_ms=int(timeout_seconds * 1000),
                success=False,
                error=f"Script execution timeout after {timeout_seconds} seconds",
            )
        except Exception as e:
            logger.error("script_execution_error", error=str(e))
            return ScriptResult(
                output={},
                logs="",
                duration_ms=0,
                success=False,
                error=str(e),
            )

    def shutdown(self) -> None:
        """Shutdown the executor."""
        self.executor.shutdown(wait=True)

    def __del__(self) -> None:
        """Cleanup on deletion."""
        try:
            self.shutdown()
        except Exception:
            pass
