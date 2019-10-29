"""
This module is a modified implementation of Python's "zipapp" module.

We've copied a lot of zipapp's code here in order to backport support for compression.
https://docs.python.org/3.7/library/zipapp.html#cmdoption-zipapp-c
"""
import contextlib
import stat
import sys
import zipapp
import zipfile

from pathlib import Path
from typing import IO, Any, Generator, Union

from . import bootstrap
from .bootstrap.environment import Environment
from .constants import BINPRM_ERROR

try:
    import importlib.resources as importlib_resources  # type: ignore
except ImportError:
    import importlib_resources  # type: ignore

# Typical maximum length for a shebang line
BINPRM_BUF_SIZE = 128

# zipapp __main__.py template
MAIN_TEMPLATE = """\
# -*- coding: utf-8 -*-
import {module}
{module}.{fn}()
"""


def write_file_prefix(f: IO[Any], interpreter: str) -> None:
    """Write a shebang line.

    :param f: An open file handle.
    :param interpreter: A path to a python interpreter.
    """
    # if the provided path is too long for a shebang we should error out
    if len(interpreter) > BINPRM_BUF_SIZE:
        sys.exit(BINPRM_ERROR)

    f.write(b"#!" + interpreter.encode(sys.getfilesystemencoding()) + b"\n")


@contextlib.contextmanager
def maybe_open(archive: Union[str, Path], mode: str) -> Generator[IO[Any], None, None]:
    if isinstance(archive, (str, Path)):
        with Path(archive).open(mode=mode) as f:
            yield f

    else:
        yield archive


def create_archive(
    source: Path, target: Path, interpreter: str, main: str, env: Environment, compressed: bool = True
) -> None:
    """Create an application archive from SOURCE.

    A modified version of stdlib's
    `zipapp.create_archive <https://docs.python.org/3/library/zipapp.html#zipapp.create_archive>`_

    """

    # Check that main has the right format.
    mod, sep, fn = main.partition(":")
    mod_ok = all(part.isidentifier() for part in mod.split("."))
    fn_ok = all(part.isidentifier() for part in fn.split("."))
    if not (sep == ":" and mod_ok and fn_ok):
        raise zipapp.ZipAppError("Invalid entry point: " + main)

    main_py = MAIN_TEMPLATE.format(module=mod, fn=fn)

    with maybe_open(target, "wb") as fd:

        # Write shebang.
        write_file_prefix(fd, interpreter)

        # Determine compression.
        compression = zipfile.ZIP_DEFLATED if compressed else zipfile.ZIP_STORED

        # Pack zipapp with dependencies.
        with zipfile.ZipFile(fd, "w", compression=compression) as z:

            site_packages = Path("site-packages")

            # Glob is known to return results in undetermenistic order.
            # We need to sort them by in-archive paths to ensure
            # that archive contents are reproducible.
            for child in sorted(source.rglob("*"), key=str):

                # Skip compiled files.
                if child.suffix == ".pyc":
                    continue

                arcname = site_packages / child.relative_to(source)
                z.write(child, arcname)

            bootstrap_target = Path("_bootstrap")

            # Write shiv's bootstrap code.
            for bootstrap_file in importlib_resources.contents(bootstrap):  # type: ignore
                if importlib_resources.is_resource(bootstrap, bootstrap_file):  # type: ignore
                    with importlib_resources.path(bootstrap, bootstrap_file) as f:  # type: ignore
                        z.write(f.absolute(), bootstrap_target / f.name)

            # write environment
            z.writestr("environment.json", env.to_json().encode("utf-8"))

            # write main
            z.writestr("__main__.py", main_py.encode("utf-8"))

    # Make pyz executable (on windows this is no-op).
    target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
