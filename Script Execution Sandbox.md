This document provides an overview of the script execution sandbox for the Kafka replay tool backend.

## Overview

The script execution sandbox is a secure, isolated environment for running user-provided Python scripts that transform Kafka message payloads. It is designed to be safe, reliable, and performant, with features like process-based isolation, timeout enforcement, and comprehensive result tracking.

## Key Components

- **`service.py`**: The main service class that provides a unified interface for script management, execution, and history tracking.
- **`runner.py`**: Implements the core script execution logic with process-based isolation and timeout enforcement.
- **`compiler.py`**: Compiles and validates Python scripts using `RestrictedPython` to prevent unsafe operations.
- **`repository.py`**: Provides async database access for scripts and their execution history.
- **`models.py`**: Contains all Pydantic and SQLAlchemy models for scripts and their execution records.

## Features

- **Secure Execution**: Scripts are executed using `RestrictedPython` to prevent access to sensitive modules like `os`, `sys`, and `subprocess`.
- **Process-Based Isolation**: Each script is executed in a separate process using `concurrent.futures.ProcessPoolExecutor`, ensuring that scripts cannot interfere with each other or the main application.
- **Timeout Enforcement**: A 2-second CPU timeout is enforced per execution to prevent runaway scripts.
- **Resource Limiting**: The maximum output payload size is limited to 1MB to prevent excessive memory usage.
- **Comprehensive Result Tracking**: The sandbox returns a typed `ScriptResult` with the transformed output, captured logs, execution duration, and success status.
- **Version Management**: Scripts are versioned in the database, and replay jobs execute the pinned version of a script, ensuring reproducibility.
- **Execution History**: Every script execution is recorded in the database for auditing and debugging purposes.

## Script Contract

User-provided scripts must adhere to a simple contract: they must define a function named `transform` that accepts a message payload `dict` and a headers `dict` and returns a modified `dict`.

```python
# Example script
def transform(message: dict, headers: dict) -> dict:
    """
    Transforms a message by adding a new field.
    """
    message["enriched"] = True
    return message
```

## Usage

The `ScriptSandboxService` should be instantiated once and used throughout the application. It requires an async SQLAlchemy session factory.

```python
# In your application startup
from app.sandbox.service import ScriptSandboxService

# Create service
sandbox_service = ScriptSandboxService(session_factory=async_session_factory)

# Create a new script
script_params = ScriptCreate(
    name="enrichment-script",
    code="def transform(message, headers):\n    message[\"enriched\"] = True\n    return message",
)
script = await sandbox_service.create_script(script_params)

# Execute the script
result = await sandbox_service.execute_script(
    code=script.code,
    message={"key": "value"},
)

if result.success:
    print(f"Transformed message: {result.output}")
else:
    print(f"Script failed: {result.error}")

# Get execution history
history, total = await sandbox_service.get_execution_history(script.id)
for record in history:
    print(f"Execution {record.id} succeeded: {record.success}")
```

## Error Handling

The sandbox is designed to be resilient to script errors. If a script fails for any reason (e.g., syntax error, timeout, unhandled exception), the service will:

1.  Capture the error message and logs.
2.  Return a `ScriptResult` with `success=False` and a detailed error message.
3.  Record the failed execution in the database.

This ensures that script errors never crash the main application and are always available for debugging.

## Security

The sandbox employs multiple layers of security to mitigate the risks of running user-provided code:

- **`RestrictedPython`**: Strips dangerous built-ins and modules from the execution environment.
- **Process Isolation**: Scripts run in separate processes, preventing them from accessing the memory or state of the main application.
- **Timeouts**: A hard timeout prevents scripts from consuming excessive CPU time.
- **Resource Limits**: Output payload size is limited to prevent memory exhaustion.

While no sandbox is perfectly secure, these measures provide a robust defense against common attack vectors.
