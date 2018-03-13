"""This module contains a simplified implementation of Python's "zipapp" module.

We've copied code here in order to patch in support for compression.
"""
import contextlib
import zipfile
import stat
import sys

from pathlib import Path
from zipapp import MAIN_TEMPLATE, ZipAppError


def write_file_prefix(f, interpreter):
    """Write a shebang line.

    :param file f: An open file handle.
    :param str interpreter: A path to a python interpreter.
    """
    shebang = b'#!' + interpreter.encode(sys.getfilesystemencoding()) + b'\n'
    f.write(shebang)


@contextlib.contextmanager
def maybe_open(archive, mode):
    if isinstance(archive, (str, Path)):
        with Path(archive).open(mode=mode) as f:
            yield f
    else:
        yield archive


def create_archive(source, target, interpreter, main, compressed=True):
    """Create an application archive from SOURCE."""

    # Check that main has the right format.
    mod, sep, fn = main.partition(':')
    mod_ok = all(part.isidentifier() for part in mod.split('.'))
    fn_ok = all(part.isidentifier() for part in fn.split('.'))
    if not (sep == ':' and mod_ok and fn_ok):
        raise ZipAppError("Invalid entry point: " + main)

    main_py = MAIN_TEMPLATE.format(module=mod, fn=fn)

    if not hasattr(target, 'write'):
        target = Path(target)

    if not hasattr(source, 'rglob'):
        source = Path(source)

    with maybe_open(target, 'wb') as fd:
        # write shebang
        write_file_prefix(fd, interpreter)

        # determine compression
        compression = zipfile.ZIP_DEFLATED if compressed else zipfile.ZIP_STORED

        # create zipapp
        with zipfile.ZipFile(fd, 'w', compression=compression) as z:
            for child in source.rglob('*'):
                arcname = child.relative_to(source)
                z.write(child, arcname.as_posix())

            # write main
            z.writestr('__main__.py', main_py.encode('utf-8'))

    # make executable
    if interpreter and not hasattr(target, 'write'):
        target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
