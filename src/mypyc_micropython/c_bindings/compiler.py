from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from mypyc_micropython.c_bindings.c_emitter import CEmitter
from mypyc_micropython.c_bindings.cmake_emitter import CMakeEmitter
from mypyc_micropython.c_bindings.stub_parser import StubParser


@dataclass
class CompilationResult:
    success: bool
    c_code: str = ""
    cmake_code: str = ""
    module_name: str = ""
    errors: list[str] = field(default_factory=list)
    output_dir: Path | None = None


class CBindingCompiler:
    def __init__(self) -> None:
        self.parser = StubParser()

    def compile_stub(
        self,
        stub_path: Path,
        output_dir: Path | None = None,
        *,
        emit_public: bool = False,
    ) -> CompilationResult:
        try:
            library = self.parser.parse_file(stub_path)
        except Exception as e:
            return CompilationResult(
                success=False,
                errors=[f"Parse error: {e}"],
            )

        if not library.header:
            return CompilationResult(
                success=False,
                module_name=library.name,
                errors=["Missing __c_header__ in stub file"],
            )

        emitter = CEmitter(library, emit_public=emit_public)
        c_code = emitter.emit()

        cmake = CMakeEmitter(library)
        cmake_code = cmake.emit()

        if output_dir:
            self._write_output(output_dir, library.name, c_code, cmake_code)

        return CompilationResult(
            success=True,
            c_code=c_code,
            cmake_code=cmake_code,
            module_name=library.name,
            output_dir=output_dir,
        )

    def compile_source(
        self,
        source: str,
        name: str = "module",
    ) -> CompilationResult:
        try:
            library = self.parser.parse_source(source, name)
        except Exception as e:
            return CompilationResult(
                success=False,
                errors=[f"Parse error: {e}"],
            )

        emitter = CEmitter(library)
        c_code = emitter.emit()

        cmake = CMakeEmitter(library)
        cmake_code = cmake.emit()

        return CompilationResult(
            success=True,
            c_code=c_code,
            cmake_code=cmake_code,
            module_name=library.name,
        )

    def _write_output(
        self,
        output_dir: Path,
        module_name: str,
        c_code: str,
        cmake_code: str,
    ) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)

        c_path = output_dir / f"{module_name}.c"
        c_path.write_text(c_code)

        cmake_path = output_dir / "micropython.cmake"
        cmake_path.write_text(cmake_code)
