"""
Async/await support demo for mypyc-micropython.

This module demonstrates compiled async functions that work with MicroPython's
uasyncio event loop. Async functions are compiled to coroutine objects with:
- State machine for suspension/resumption at await points
- __await__() method for awaitable protocol
- send() method for receiving values from the event loop

Usage with uasyncio:
    import asyncio
    import async_demo

    async def main():
        result = await async_demo.compute_sum(100)
        print(f"Sum: {result}")

    asyncio.run(main())

Note: The 'asyncio' module is imported at runtime by the generated C code.
Type hints are provided by examples/asyncio.pyi stub file.
"""

import asyncio  # Runtime import via generated C code (see asyncio.pyi for types)


async def simple_return() -> int:
    """Simple async function that immediately returns."""
    return 42


async def compute_sum(n: int) -> int:
    """Compute sum from 0 to n-1.

    This is a simple async function with no await points - it demonstrates
    that async functions can also perform synchronous computation.
    """
    total: int = 0
    i: int = 0
    while i < n:
        total = total + i
        i = i + 1
    return total


async def sequential_operations() -> int:
    """Async function performing simple sequential arithmetic.

    This coroutine has no await points and simply returns the sum
    of two integers. Demonstrates basic async function structure.
    """
    a: int = 10
    b: int = 20
    # In real code, these would await actual async operations
    result: int = a + b
    return result


async def with_parameters(x: int, y: int) -> int:
    """Async function with multiple parameters.

    Parameters are stored in the coroutine struct and preserved
    across await points.
    """
    return x + y


async def delayed_double(n: int) -> int:
    """Double a number after yielding to the event loop.

    Demonstrates await asyncio.sleep() - the most common async pattern.
    The sleep(0) yields control to the event loop without actual delay.
    """
    await asyncio.sleep(0)
    return n * 2


async def countdown_with_delay(start: int) -> int:
    """Count down from start, yielding between each step.

    Demonstrates multiple awaits in a loop - each await becomes
    a suspension point where other tasks can run.
    """
    count: int = start
    while count > 0:
        await asyncio.sleep(0)
        count = count - 1
    return count
