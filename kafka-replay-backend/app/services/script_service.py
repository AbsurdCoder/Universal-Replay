"""Service for enrichment script management."""

from typing import Dict, Any

from app.sandbox import get_executor
from app.core.logging import get_logger

logger = get_logger(__name__)


class ScriptService:
    """Service for managing and executing enrichment scripts."""

    def __init__(self):
        """Initialize script service."""
        self.executor = get_executor()
        # In-memory script storage (replace with database in production)
        self._scripts: Dict[str, str] = {}

    async def register_script(self, name: str, code: str) -> None:
        """Register an enrichment script."""
        try:
            # Validate by compiling
            from RestrictedPython import compile_restricted

            byte_code = compile_restricted(code, filename="<script>", mode="exec")
            if byte_code.errors:
                errors = "; ".join(str(e) for e in byte_code.errors)
                raise ValueError(f"Script compilation failed: {errors}")

            self._scripts[name] = code
            logger.info("Registered enrichment script", name=name)

        except Exception as e:
            logger.error("Failed to register script", name=name, error=str(e))
            raise

    async def get_script(self, name: str) -> str:
        """Get a registered script."""
        if name not in self._scripts:
            raise ValueError(f"Script '{name}' not found")
        return self._scripts[name]

    async def list_scripts(self) -> list[str]:
        """List all registered scripts."""
        return list(self._scripts.keys())

    async def delete_script(self, name: str) -> None:
        """Delete a registered script."""
        if name not in self._scripts:
            raise ValueError(f"Script '{name}' not found")
        del self._scripts[name]
        logger.info("Deleted enrichment script", name=name)

    async def enrich_message(self, script_name: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich a message using a registered script.

        Args:
            script_name: Name of the registered script
            message: Message to enrich

        Returns:
            Enriched message

        Raises:
            ValueError: If script not found or execution fails
        """
        try:
            script_code = await self.get_script(script_name)
            enriched = await self.executor.enrich_message(script_code, message)

            logger.debug("Message enriched", script_name=script_name)

            return enriched

        except Exception as e:
            logger.error("Failed to enrich message", script_name=script_name, error=str(e))
            raise
