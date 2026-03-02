"""Script execution sandbox using RestrictedPython."""

import asyncio
import json
from typing import Any, Dict, Optional
from RestrictedPython import compile_restricted, safe_globals

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ScriptExecutor:
    """Execute user-defined scripts in a restricted sandbox."""

    def __init__(self):
        """Initialize script executor."""
        self.timeout = settings.SCRIPT_EXECUTION_TIMEOUT
        self.safe_builtins = {
            "print": print,
            "len": len,
            "range": range,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "tuple": tuple,
            "set": set,
            "json": json,
            "Exception": Exception,
            "ValueError": ValueError,
            "TypeError": TypeError,
        }

    async def execute(
        self,
        script_code: str,
        function_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Execute a script function in a restricted sandbox.

        Args:
            script_code: Python source code to execute
            function_name: Name of the function to call
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            Result of the function execution

        Raises:
            ValueError: If script compilation or execution fails
            asyncio.TimeoutError: If execution exceeds timeout
        """
        try:
            # Compile the script with RestrictedPython
            byte_code = compile_restricted(script_code, filename="<script>", mode="exec")

            if byte_code.errors:
                error_msg = "; ".join(str(e) for e in byte_code.errors)
                logger.error("Script compilation failed", errors=error_msg)
                raise ValueError(f"Script compilation failed: {error_msg}")

            # Create a restricted execution environment
            restricted_globals = {
                "__builtins__": self.safe_builtins,
                "_print_": print,
                "_getattr_": getattr,
                "__name__": "restricted_script",
                "__metaclass__": type,
            }

            # Execute the compiled code
            exec(byte_code.code, restricted_globals)

            # Get the function to execute
            if function_name not in restricted_globals:
                raise ValueError(f"Function '{function_name}' not found in script")

            func = restricted_globals[function_name]

            if not callable(func):
                raise ValueError(f"'{function_name}' is not callable")

            # Execute with timeout
            logger.debug(
                "Executing script function",
                function_name=function_name,
                timeout=self.timeout,
            )

            result = await asyncio.wait_for(
                self._run_function(func, args, kwargs),
                timeout=self.timeout,
            )

            logger.debug("Script execution completed", function_name=function_name)
            return result

        except asyncio.TimeoutError:
            logger.error("Script execution timeout", function_name=function_name, timeout=self.timeout)
            raise
        except ValueError as e:
            logger.error("Script execution error", error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected script execution error", error=str(e), error_type=type(e).__name__)
            raise ValueError(f"Script execution failed: {str(e)}")

    async def _run_function(self, func, args, kwargs) -> Any:
        """Run a function, handling both sync and async functions."""
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            # Run sync function in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


class EnrichmentScriptExecutor(ScriptExecutor):
    """Specialized executor for message enrichment scripts."""

    async def enrich_message(self, script_code: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an enrichment script on a message.

        The script should define an `enrich(message)` function that:
        - Takes a dict (the message)
        - Returns a dict (the enriched message)

        Args:
            script_code: Python source code with an `enrich` function
            message: Message to enrich

        Returns:
            Enriched message

        Raises:
            ValueError: If script execution fails
        """
        try:
            enriched = await self.execute(script_code, "enrich", message)

            if not isinstance(enriched, dict):
                raise ValueError(f"Enrichment function must return a dict, got {type(enriched).__name__}")

            return enriched

        except Exception as e:
            logger.error("Message enrichment failed", error=str(e))
            raise


# Global executor instance
_executor: Optional[EnrichmentScriptExecutor] = None


def get_executor() -> EnrichmentScriptExecutor:
    """Get the global script executor instance."""
    global _executor
    if _executor is None:
        _executor = EnrichmentScriptExecutor()
    return _executor
