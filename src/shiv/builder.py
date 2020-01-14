"""
This module is a modified implementation of Python's "zipapp" module.

We've copied a lot of zipapp's code here in order to backport support for compression.
https://docs.python.org/3.7/library/zipapp.html#cmdoption-zipapp-c
"""
import hashlib
import os
import stat
import sys
import time
import zipapp
import zipfile

from datetime import datetime, timezone
from pathlib import Path
from typing import IO, Any, List, Optional, Tuple, Union

from . import bootstrap
from .bootstrap.environment import Environment
from .constants import BINPRM_ERROR, BUILD_AT_TIMESTAMP_FORMAT

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


def _write_to_zipapp(
    arhive: zipfile.ZipFile,
    arcname: str,
    data_source: Union[Path, bytes],
    date_time: Tuple[int, int, int, int, int, int],
    compression: int,
    contents_hash: hashlib.sha3_256,
) -> None:
    """Write a file or a bytestring to a ZipFile as a separate entry and
    update contents_hash as a side effect

    The approach is borrowed from 'wheel' code.
    """
    if isinstance(data_source, Path):
        with data_source.open("rb") as f:
            data = f.read()
            st: Optional[os.stat_result] = os.fstat(f.fileno())
    else:
        data = data_source
        st = None

    contents_hash.update(data)

    zinfo = zipfile.ZipInfo(arcname, date_time=date_time)
    zinfo.compress_type = compression
    if st is not None:
        zinfo.external_attr = (stat.S_IMODE(st.st_mode) | stat.S_IFMT(st.st_mode)) << 16

    arhive.writestr(zinfo, data)


def create_archive(
    sources: List[Path], target: Path, interpreter: str, main: str, env: Environment, compressed: bool = True
) -> None:
    """Create an application archive from SOURCE.

    This function is a heavily modified version of stdlib's
    `zipapp.create_archive <https://docs.python.org/3/library/zipapp.html#zipapp.create_archive>`_

    """

    # Check that main has the right format.
    mod, sep, fn = main.partition(":")
    mod_ok = all(part.isidentifier() for part in mod.split("."))
    fn_ok = all(part.isidentifier() for part in fn.split("."))
    if not (sep == ":" and mod_ok and fn_ok):
        raise zipapp.ZipAppError("Invalid entry point: " + main)

    # Collect our timestamp data and create our content hash.
    main_py = MAIN_TEMPLATE.format(module=mod, fn=fn)
    timestamp = datetime.strptime(env.built_at, BUILD_AT_TIMESTAMP_FORMAT).replace(tzinfo=timezone.utc).timestamp()
    zipinfo_datetime: Tuple[int, int, int, int, int, int] = time.gmtime(int(timestamp))[0:6]
    contents_hash = hashlib.sha256()

    with target.open(mode="wb") as fd:

        # Write shebang.
        write_file_prefix(fd, interpreter)

        # Determine compression.
        compression = zipfile.ZIP_DEFLATED if compressed else zipfile.ZIP_STORED

        # Pack zipapp with dependencies.
        with zipfile.ZipFile(fd, "w", compression=compression) as archive:

            site_packages = Path("site-packages")

            for source in sources:

                # Glob is known to return results in non-determenistic order.
                # We need to sort them by in-archive paths to ensure
                # that archive contents are reproducible.
                for child in sorted(source.rglob("*"), key=str):

                    # Skip compiled files and directories (as they are not required to be present in the zip).
                    if child.suffix == ".pyc" or child.is_dir():
                        continue

                    arcname = str(site_packages / child.relative_to(source))
                    _write_to_zipapp(archive, arcname, child, zipinfo_datetime, compression, contents_hash)

            bootstrap_target = Path("_bootstrap")

            # Write shiv's bootstrap code.
            for bootstrap_file in importlib_resources.contents(bootstrap):  # type: ignore
                if importlib_resources.is_resource(bootstrap, bootstrap_file):  # type: ignore
                    with importlib_resources.path(bootstrap, bootstrap_file) as f:  # type: ignore
                        _write_to_zipapp(
                            archive,
                            str(bootstrap_target / f.name),
                            f.absolute(),
                            zipinfo_datetime,
                            compression,
                            contents_hash,
                        )

            if contents_hash is not None:
                env.build_id = contents_hash.hexdigest()

            # Write environment info in json file.
            #
            # The environment file contains build_id which is a SHA-256 checksum of all **site-packages** contents.
            # environment.json and __main__.py are not used to calculate the checksum, is it's only used for local
            # caching of site-packages and these files are always read from archive.
            _write_to_zipapp(
                archive, "environment.json", env.to_json().encode("utf-8"), zipinfo_datetime, compression, contents_hash
            )

            # write main
            _write_to_zipapp(
                archive, "__main__.py", main_py.encode("utf-8"), zipinfo_datetime, compression, contents_hash
            )

    # Make pyz executable (on windows this is no-op).
    target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
