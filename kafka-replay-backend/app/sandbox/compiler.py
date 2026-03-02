"""
RestrictedPython code compilation and validation.

Compiles and validates Python scripts using RestrictedPython to prevent unsafe operations.
"""

import structlog
from typing import Optional, Tuple
from RestrictedPython import compile_restricted
from RestrictedPython.Guards import guarded_inplacebinary_op, guarded_iter_unpack_sequence

logger = structlog.get_logger(__name__)


class ScriptCompiler:
    """Compiles and validates scripts using RestrictedPython."""

    # Forbidden names that should not be accessible
    FORBIDDEN_NAMES = {
        "__import__",
        "__builtins__",
        "_getattr_",
        "_write_",
        "_getitem_",
        "_getiter_",
        "_iter_unpack_sequence_",
        "exec",
        "eval",
        "compile",
        "open",
        "file",
        "input",
        "raw_input",
        "reload",
        "execfile",
    }

    # Allowed builtins
    ALLOWED_BUILTINS = {
        "abs": abs,
        "all": all,
        "any": any,
        "bin": bin,
        "bool": bool,
        "bytearray": bytearray,
        "bytes": bytes,
        "chr": chr,
        "dict": dict,
        "divmod": divmod,
        "enumerate": enumerate,
        "filter": filter,
        "float": float,
        "format": format,
        "frozenset": frozenset,
        "hex": hex,
        "int": int,
        "isinstance": isinstance,
        "issubclass": issubclass,
        "iter": iter,
        "len": len,
        "list": list,
        "map": map,
        "max": max,
        "min": min,
        "next": next,
        "oct": oct,
        "ord": ord,
        "pow": pow,
        "range": range,
        "reversed": reversed,
        "round": round,
        "set": set,
        "slice": slice,
        "sorted": sorted,
        "str": str,
        "sum": sum,
        "tuple": tuple,
        "type": type,
        "zip": zip,
        "True": True,
        "False": False,
        "None": None,
        "Exception": Exception,
        "ValueError": ValueError,
        "TypeError": TypeError,
        "KeyError": KeyError,
        "IndexError": IndexError,
        "RuntimeError": RuntimeError,
    }

    @staticmethod
    def compile(code: str) -> Tuple[Optional[object], Optional[str]]:
        """
        Compile a script using RestrictedPython.

        Args:
            code: Python script code.

        Returns:
            Tuple of (compiled_code, error_message).
            If successful, compiled_code is not None and error_message is None.
            If failed, compiled_code is None and error_message contains details.
        """
        try:
            # Compile with RestrictedPython
            compiled = compile_restricted(code, filename="<script>", mode="exec")

            # Check for compilation errors
            if compiled.errors:
                error_msg = "; ".join(str(e) for e in compiled.errors)
                logger.warning("script_compilation_errors", errors=error_msg)
                return None, f"Compilation errors: {error_msg}"

            if compiled.warnings:
                logger.info("script_compilation_warnings", warnings=compiled.warnings)

            # Check for forbidden names
            if compiled.code is None:
                return None, "Compilation resulted in no code"

            # Validate that the code doesn't contain forbidden names
            forbidden_found = []
            for name in compiled.names:
                if name in ScriptCompiler.FORBIDDEN_NAMES:
                    forbidden_found.append(name)

            if forbidden_found:
                error_msg = f"Forbidden names: {', '.join(forbidden_found)}"
                logger.warning("script_forbidden_names", names=forbidden_found)
                return None, error_msg

            logger.info("script_compiled_successfully")
            return compiled.code, None

        except SyntaxError as e:
            error_msg = f"Syntax error: {str(e)}"
            logger.warning("script_syntax_error", error=error_msg)
            return None, error_msg

        except Exception as e:
            error_msg = f"Compilation failed: {str(e)}"
            logger.error("script_compilation_failed", error=error_msg)
            return None, error_msg

    @staticmethod
    def validate_syntax(code: str) -> Tuple[bool, Optional[str]]:
        """
        Validate script syntax without full compilation.

        Args:
            code: Python script code.

        Returns:
            Tuple of (is_valid, error_message).
        """
        try:
            compile(code, filename="<script>", mode="exec")
            return True, None
        except SyntaxError as e:
            return False, f"Syntax error: {str(e)}"
        except Exception as e:
            return False, f"Validation failed: {str(e)}"

    @staticmethod
    def get_safe_globals() -> dict:
        """
        Get a safe globals dictionary for script execution.

        Returns:
            Dictionary of safe globals.
        """
        return {
            "__builtins__": ScriptCompiler.ALLOWED_BUILTINS,
            "_getattr_": getattr,
            "_write_": lambda x: x,
            "_getitem_": lambda obj, index: obj[index],
            "_getiter_": iter,
            "_iter_unpack_sequence_": guarded_iter_unpack_sequence,
            "__name__": "restricted_script",
            "__metaclass__": type,
            "_inplacebinary_": guarded_inplacebinary_op,
        }

    @staticmethod
    def get_safe_locals() -> dict:
        """
        Get a safe locals dictionary for script execution.

        Returns:
            Dictionary of safe locals.
        """
        return {}
