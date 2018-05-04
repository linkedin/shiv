"""
The code in this module is adapted from https://github.com/pantsbuild/pex/blob/master/pex/pex.py

It is used to enter an interactive interpreter session from an executable created with ``shiv``.
"""
import code
import sys


def _exec_function(ast, globals_map):
    locals_map = globals_map
    exec(ast, globals_map, locals_map)
    return locals_map


def execute_content(name, content):
    try:
        ast = compile(content, name, "exec", flags=0, dont_inherit=1)
    except SyntaxError:
        raise RuntimeError(
            f"Unable to parse {name}. Is it a Python script? Syntax correct?"
        )

    old_name, old_file = globals().get("__name__"), globals().get("__file__")

    try:
        globals()["__name__"] = "__main__"
        globals()["__file__"] = name
        _exec_function(ast, globals())
    finally:
        if old_name:
            globals()["__name__"] = old_name
        else:
            globals().pop("__name__")
        if old_file:
            globals()["__file__"] = old_file
        else:
            globals().pop("__file__")


def execute_interpreter():
    if sys.argv[1:]:
        try:
            with open(sys.argv[1]) as fp:
                name, content = sys.argv[1], fp.read()
        except (FileNotFoundError, IsADirectoryError, PermissionError) as e:
            raise RuntimeError(
                f"Could not open {sys.argv[1]} in the environment [{sys.argv[0]}]: {e}"
            )

        sys.argv = sys.argv[1:]
        execute_content(name, content)
    else:
        code.interact()
