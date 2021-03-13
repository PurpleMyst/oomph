from __future__ import annotations

import argparse
import os
import pathlib
import shlex
import signal
import subprocess
import sys
import traceback
from typing import Dict, List

from pyoomph import ast, ast2ir, c_output, parser

python_code_dir = pathlib.Path(__file__).absolute().parent
project_root = python_code_dir.parent


def _get_compiled_file_name(
    source_path: pathlib.Path, compilation_dir: pathlib.Path
) -> str:
    # TODO: avoid long file names
    return (
        os.path.relpath(source_path, compilation_dir.parent)
        .replace(".", "_dot_")
        .replace(os.sep, "_slash_")
    )


class CompilationUnit:
    ast: List[ast.ToplevelDeclaration]

    def __init__(self, source_path: pathlib.Path, session: c_output.Session):
        self.session = session
        name = _get_compiled_file_name(source_path, session.compilation_dir)
        self.source_path = source_path
        self.c_path = session.compilation_dir / (name + ".c")
        self.h_path = session.compilation_dir / (name + ".h")

    def create_untyped_ast(self) -> None:
        source_code = self.source_path.read_text(encoding="utf-8")
        self.ast = parser.parse_file(
            source_code, self.source_path, project_root / "stdlib"
        )

    def create_c_and_h_files(
        self,
        headers: List[str],
    ) -> None:
        try:
            ir = ast2ir.convert_program(
                self.ast, self.source_path, self.session.exports
            )
            c, h = self.session.create_c_code(ir, self.source_path, headers)
        except Exception:
            traceback.print_exc()
            print(
                f"\nThis happened while compiling {self.source_path}", file=sys.stderr
            )
            sys.exit(1)

        self.c_path.write_text(c, encoding="utf-8")
        self.h_path.write_text(h, encoding="utf-8")


def get_c_compiler_command(
    c_paths: List[pathlib.Path], exepath: pathlib.Path
) -> List[str]:
    compile_info = {}
    with (project_root / "obj" / "compile_info.txt").open() as file:
        for line in file:
            key, value = line.rstrip("\n").split("=", maxsplit=1)
            compile_info[key] = value

    return (
        [compile_info["cc"]]
        + shlex.split(compile_info["cflags"])
        + [str(path) for path in project_root.glob("obj/*.o")]
        + [str(path) for path in c_paths]
        + ["-o", str(exepath)]
        + shlex.split(compile_info["ldflags"])
        + ["-I", str(project_root)]
    )


def run(command: List[str], verbose: bool) -> int:
    if verbose:
        print("Running:", " ".join(map(shlex.quote, command)), file=sys.stderr)
    return subprocess.run(command).returncode


def main() -> None:
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("infile", type=pathlib.Path)
    arg_parser.add_argument("--valgrind", action="store_true")
    arg_parser.add_argument("-v", "--verbose", action="store_true")
    compiler_args, program_args = arg_parser.parse_known_args()

    try:
        cache_dir = compiler_args.infile.parent / ".oomph-cache"
        cache_dir.mkdir(exist_ok=True)
    except OSError:
        cache_dir = pathlib.Path.cwd() / ".oomph-cache"
        cache_dir.mkdir(exist_ok=True)

    exe_path = cache_dir / compiler_args.infile.stem
    session = c_output.Session(cache_dir / (exe_path.stem + "_compilation"))
    session.compilation_dir.mkdir(exist_ok=True)

    all_compilation_units: List[CompilationUnit] = []
    dependencies: Dict[pathlib.Path, List[pathlib.Path]] = {}
    todo_list = [compiler_args.infile.absolute()]
    while todo_list:
        source_path = todo_list.pop()
        if source_path in dependencies:
            continue

        if compiler_args.verbose:
            print("Parsing", source_path)

        unit = CompilationUnit(source_path, session)
        all_compilation_units.append(unit)
        unit.create_untyped_ast()

        deps = [
            top_declaration.path
            for top_declaration in unit.ast
            if isinstance(top_declaration, ast.Import)
        ]
        if source_path != project_root / "builtins.oomph":
            deps.append(project_root / "builtins.oomph")
        dependencies[unit.source_path] = deps
        todo_list.extend(deps)

    # Dumbest toposort you have ever seen
    compilation_order: List[CompilationUnit] = []
    while len(compilation_order) < len(dependencies):
        unit = [u for u in all_compilation_units if u not in compilation_order][0]
        decisions = [unit]
        while True:
            need_first = [
                u
                for u in all_compilation_units
                if u not in compilation_order
                and u.source_path in dependencies[unit.source_path]
            ]
            if not need_first:
                break
            if compiler_args.verbose:
                print(
                    f"Noticed dependency: {unit.source_path} --> {need_first[0].source_path}"
                )
            unit = need_first[0]
            decisions.append(unit)
            if decisions.count(unit) >= 2:
                raise RuntimeError(
                    "cyclic imports: "
                    + " --> ".join(d.source_path.name for d in decisions)
                )
        compilation_order.append(unit)

    for index, unit in enumerate(compilation_order):
        if compiler_args.verbose:
            print("Creating c and h files:", unit.source_path)
        already_compiled = compilation_order[:index]
        unit.create_c_and_h_files([unit.h_path.name for unit in already_compiled])

    command = get_c_compiler_command(
        [unit.c_path for unit in all_compilation_units], exe_path
    )

    result = run(command, compiler_args.verbose)
    if result != 0:
        sys.exit(result)

    command = []
    if compiler_args.valgrind:
        command.extend(
            [
                "valgrind",
                "-q",
                "--leak-check=full",
                "--show-leak-kinds=all",
            ]
        )
    command.extend([str(exe_path)] + program_args)

    result = run(command, compiler_args.verbose)
    if result < 0:  # killed by signal
        message = f"Program killed by signal {abs(result)}"
        try:
            message += f" ({signal.Signals(abs(result)).name})"
        except ValueError:  # e.g. SIGRTMIN + 1
            pass
        print(message, file=sys.stderr)
    sys.exit(result)


main()
