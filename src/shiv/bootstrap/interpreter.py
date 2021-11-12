"""
The code in this module is adapted from https://github.com/pantsbuild/pex/blob/master/pex/pex.py

It is used to enter an interactive interpreter session from an executable created with ``shiv``.
"""
import code
import runpy
import sys

from pathlib import Path


def _exec_function(ast, globals_map):
    locals_map = globals_map
    exec(ast, globals_map, locals_map)
    return locals_map


def execute_content(name, content, argv0=None):
    argv0 = argv0 or name

    try:
        ast = compile(content, name, "exec", flags=0, dont_inherit=1)
    except SyntaxError:
        raise RuntimeError(f"Unable to parse {name}. Is it a Python script? Syntax correct?")

    sys.argv[0] = argv0
    globals_ = globals().copy()
    globals_["__name__"] = "__main__"
    globals_["__file__"] = name
    _exec_function(ast, globals_)


def execute_module(module_name):
    runpy.run_module(module_name, run_name="__main__")


def execute_interpreter():
    args = sys.argv[1:]

    if args:

        arg = args[0]

        if arg == "-c":
            content = args[1]
            sys.argv = [arg, *args[2:]]
            execute_content("-c <cmd>", content, argv0=arg)

        elif arg == "-m":
            module = args[1]
            sys.argv = args[1:]
            execute_module(module)

        else:
            if arg == "-":
                content = sys.stdin.read()

            else:
                try:
                    content = Path(arg).read_text()
                except (FileNotFoundError, IsADirectoryError, PermissionError) as e:
                    raise RuntimeError(f"Could not open '{arg}' in the environment [{sys.argv[0]}]: {e}")

            sys.argv = args
            execute_content(arg, content)

    else:
        code.interact()
