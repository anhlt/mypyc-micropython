"""Type stub for asyncio module.

This stub provides type hints for asyncio functions used in compiled modules.
The actual asyncio module is imported at runtime by the generated C code via
mp_import_name().

Note: This is NOT a real Python module - it's only used for type checking.
"""

from typing import Any, Coroutine

def sleep(delay: float) -> Coroutine[Any, Any, None]:
    """Sleep for the given number of seconds.

    In MicroPython, this is provided by the uasyncio module.
    The delay is in seconds (can be fractional).
    """
    ...

def sleep_ms(delay: int) -> Coroutine[Any, Any, None]:
    """Sleep for the given number of milliseconds.

    MicroPython-specific function for millisecond delays.
    """
    ...
