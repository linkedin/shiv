"""This module contains a simplified implementation of Python's "zipapp" module.

We've copied code here in order to patch in support for compression.
"""
import contextlib
import zipfile
import stat
import sys
import zipapp

from pathlib import Path
from typing import Any, IO, Generator, Union

# Typical maximum length for a shebang line
BINPRM_BUF_SIZE = 128

# zipapp __main__.py template
MAIN_TEMPLATE = """\
# -*- coding: utf-8 -*-
import {module}
{module}.{fn}()
"""


def write_file_prefix(f: IO[Any], interpreter_path: Path) -> None:
    """Write a shebang line.

    :param f: An open file handle.
    :param interpreter_path: A path to a python interpreter.
    """

    # fall back to /usr/bin/env if the interp path is too long
    if len(interpreter_path.as_posix()) > BINPRM_BUF_SIZE:
        shebang = f'/usr/bin/env {interpreter_path.name}'
    else:
        shebang = interpreter_path.as_posix()

    f.write(
        b'#!' + shebang.encode(sys.getfilesystemencoding()) + b'\n'
    )


@contextlib.contextmanager
def maybe_open(archive: Union[str, Path], mode: str) -> Generator[IO[Any], None, None]:
    if isinstance(archive, (str, Path)):
        with Path(archive).open(mode=mode) as f:
            yield f
    else:
        yield archive


def create_archive(
    source: Path,
    target: Path,
    interpreter: Path,
    main: str,
    compressed: bool = True,
) -> None:
    """Create an application archive from SOURCE."""

    # Check that main has the right format.
    mod, sep, fn = main.partition(':')
    mod_ok = all(part.isidentifier() for part in mod.split('.'))
    fn_ok = all(part.isidentifier() for part in fn.split('.'))
    if not (sep == ':' and mod_ok and fn_ok):
        raise zipapp.ZipAppError("Invalid entry point: " + main)

    main_py = MAIN_TEMPLATE.format(module=mod, fn=fn)

    with maybe_open(target, 'wb') as fd:
        # write shebang
        write_file_prefix(fd, interpreter)

        # determine compression
        compression = zipfile.ZIP_DEFLATED if compressed else zipfile.ZIP_STORED

        # create zipapp
        with zipfile.ZipFile(fd, 'w', compression=compression) as z:
            for child in source.rglob('*'):
                arcname = child.relative_to(source)
                z.write(child.as_posix(), arcname.as_posix())

            # write main
            z.writestr('__main__.py', main_py.encode('utf-8'))

    # make executable
    if interpreter and not hasattr(target, 'write'):
        target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
