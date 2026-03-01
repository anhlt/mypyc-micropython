"""Generate micropython.cmake build files from CLibraryDef."""

from __future__ import annotations

from mypyc_micropython.c_bindings.c_ir import CLibraryDef


class CMakeEmitter:
    def __init__(self, library: CLibraryDef) -> None:
        self.lib = library

    def emit(self) -> str:
        lines: list[str] = []
        name = self.lib.name
        target = f"usermod_{name}"

        lines.append(f"add_library({target} INTERFACE)")
        lines.append("")

        lines.append(f"target_sources({target} INTERFACE")
        lines.append(f"    ${{CMAKE_CURRENT_LIST_DIR}}/{name}.c")
        lines.append(")")
        lines.append("")

        include_dirs = ["${CMAKE_CURRENT_LIST_DIR}"]
        include_dirs.extend(self.lib.include_dirs)
        lines.append(f"target_include_directories({target} INTERFACE")
        for d in include_dirs:
            lines.append(f"    {d}")
        lines.append(")")
        lines.append("")

        if self.lib.libraries:
            lines.append(f"target_link_libraries({target} INTERFACE")
            for lib in self.lib.libraries:
                lines.append(f"    {lib}")
            lines.append(")")
            lines.append("")

        if self.lib.defines:
            lines.append(f"target_compile_definitions({target} INTERFACE")
            for define in self.lib.defines:
                lines.append(f"    {define}")
            lines.append(")")
            lines.append("")

        lines.append(f"target_link_libraries(usermod INTERFACE {target})")

        return "\n".join(lines)
