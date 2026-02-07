# mypyc-micropython Documentation

This directory contains documentation for the mypyc-micropython project - a compiler that transforms typed Python code into MicroPython-compatible C extension modules.

## Documentation Index

| Document | Description |
|----------|-------------|
| [01-architecture.md](01-architecture.md) | System architecture, compilation pipeline, design decisions |
| [02-mypyc-reference.md](02-mypyc-reference.md) | How mypyc implements complex features (*args, **kwargs, closures, generators) |
| [03-micropython-c-api.md](03-micropython-c-api.md) | MicroPython C API quick reference |
| [04-feature-scope.md](04-feature-scope.md) | Feature scope definition (in-scope, partial, out-of-scope) |
| [05-roadmap.md](05-roadmap.md) | 6-phase implementation roadmap |
| [06-esp32-integration.md](06-esp32-integration.md) | Calling ESP32 MicroPython modules from compiled code |
| [07-micropython-async-internals.md](07-micropython-async-internals.md) | Deep dive into MicroPython's async/await implementation |

## Quick Links

### For Users
- [Getting Started](../README.md) - Installation and basic usage
- [Supported Features](04-feature-scope.md#in-scope-features) - What Python features are supported
- [ESP32 Integration](06-esp32-integration.md) - Using hardware modules

### For Contributors
- [Architecture Overview](01-architecture.md) - How the compiler works
- [mypyc Reference](02-mypyc-reference.md) - Learn from mypyc's implementation
- [Implementation Roadmap](05-roadmap.md) - What's planned next

## Project Status

**Current State:** Working proof-of-concept compiler (AST → C)

**Supports:**
- Basic functions with type annotations
- Primitives: `int`, `float`, `bool`
- Arithmetic, comparison, bitwise operators
- Control flow: `if`/`else`, `while` loops
- Recursion
- Local variables

**Coming Soon:**
- `for` loops
- Lists and dictionaries
- Simple classes
- Exception handling

## External References

- [mypyc Documentation](https://mypyc.readthedocs.io/en/latest/)
- [MicroPython Documentation](https://docs.micropython.org/)
- [MicroPython C Modules](https://docs.micropython.org/en/latest/develop/cmodules.html)
- [ESP32 MicroPython Quick Reference](https://docs.micropython.org/en/latest/esp32/quickref.html)
