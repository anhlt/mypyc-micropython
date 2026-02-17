from __future__ import annotations

import importlib
import subprocess
from pathlib import Path

import pytest


def _rewrite_generated_includes(c_code: str) -> str:
    return (
        c_code.replace('#include "py/runtime.h"', '#include "runtime.h"')
        .replace('#include "py/obj.h"', '#include "runtime.h"')
        .replace('#include "py/objtype.h"', '#include "runtime.h"')
    )


@pytest.fixture
def compile_and_run(tmp_path: Path):
    mock_include_dir = Path(__file__).parent / "mock_mp"
    compile_source = importlib.import_module("mypyc_micropython.compiler").compile_source

    def _run(python_source: str, module_name: str, test_main_c: str) -> str:
        generated_c = compile_source(python_source, module_name)
        generated_c = _rewrite_generated_includes(generated_c)

        test_c_path = tmp_path / f"{module_name}_runtime_test.c"
        binary_path = tmp_path / f"{module_name}_runtime_test"

        test_c_path.write_text(f"{generated_c}\n\n{test_main_c}\n")

        compile_cmd = [
            "/usr/bin/gcc",
            "-std=c99",
            "-Wall",
            "-Werror",
            "-Wno-unused-function",
            "-Wno-unused-const-variable",
            "-I",
            str(mock_include_dir),
            str(test_c_path),
            "-o",
            str(binary_path),
        ]
        compile_proc = subprocess.run(compile_cmd, capture_output=True, text=True)
        if compile_proc.returncode != 0:
            raise RuntimeError(
                "gcc compilation failed\n"
                f"command: {' '.join(compile_cmd)}\n"
                f"stdout:\n{compile_proc.stdout}\n"
                f"stderr:\n{compile_proc.stderr}"
            )

        run_proc = subprocess.run([str(binary_path)], capture_output=True, text=True)
        if run_proc.returncode != 0:
            raise RuntimeError(
                "compiled binary failed\n"
                f"exit_code: {run_proc.returncode}\n"
                f"stdout:\n{run_proc.stdout}\n"
                f"stderr:\n{run_proc.stderr}"
            )

        return run_proc.stdout

    return _run
