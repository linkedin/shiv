import hashlib
import os
import shutil
import sys
import time

from configparser import ConfigParser
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Optional

import click

from . import __version__
from . import builder, pip
from .bootstrap.environment import Environment
from .constants import (
    BUILD_AT_TIMESTAMP_FORMAT,
    DEFAULT_SHEBANG,
    DISALLOWED_ARGS,
    DISALLOWED_PIP_ARGS,
    NO_ENTRY_POINT,
    NO_OUTFILE,
    NO_PIP_ARGS_OR_SITE_PACKAGES,
    SOURCE_DATE_EPOCH_DEFAULT,
    SOURCE_DATE_EPOCH_ENV,
)


def find_entry_point(site_packages_dirs: List[Path], console_script: str) -> str:
    """Find a console_script in a site-packages directory.

    Console script metadata is stored in entry_points.txt per setuptools
    convention. This function searches all entry_points.txt files and
    returns the import string for a given console_script argument.

    :param site_packages_dirs: Paths to site-packages directories on disk.
    :param console_script: A console_script string.
    """

    config_parser = ConfigParser()

    for site_packages in site_packages_dirs:
        # noinspection PyTypeChecker
        config_parser.read(site_packages.rglob("entry_points.txt"))

    return config_parser["console_scripts"][console_script]


def console_script_exists(site_packages_dirs: List[Path], console_script: str) -> bool:
    """Return true if the console script with provided name exists in one of the site-packages directories.

    Console script is expected to be in the 'bin' directory of site packages.

    :param site_packages_dirs: Paths to site-packages directories on disk.
    :param console_script: A console script name.
    """

    for site_packages in site_packages_dirs:

        if (site_packages / "bin" / console_script).exists():
            return True

    return False


def copytree(src: Path, dst: Path) -> None:
    """A utility function for syncing directories.

    This function is based on shutil.copytree. In Python versions that are
    older than 3.8, shutil.copytree would raise FileExistsError if the "dst"
    directory already existed.

    """

    # Make our target (if it doesn't already exist).
    dst.mkdir(parents=True, exist_ok=True)

    for path in src.iterdir():  # type: Path

        # If we encounter a subdirectory, recurse.
        if path.is_dir():
            copytree(path, dst / path.relative_to(src))

        else:
            shutil.copy2(str(path), str(dst / path.relative_to(src)))


def main(
    *,
    output_file: str,
    entry_point: Optional[str] = None,
    console_script: Optional[str] = None,
    python: Optional[str] = None,
    site_packages: Optional[str] = None,
    build_id: Optional[str] = None,
    # Optional switches and flags
    compressed: bool = True,
    # Default inactive flags
    compile_pyc: bool = False,
    extend_pythonpath: bool = False,
    reproducible: bool = False,
    no_modify: bool = False,
    preamble: Optional[str] = None,
    root: Optional[str] = None,
    # Unprocessed args passed to pip
    pip_args: Optional[List[str]] = None
) -> None:
    """ Main routine wrapped by `shiv` command.

    Enables direct use from python scripts:

    .. code-block:: py

        >>> main(output_file='numpy.pyz', compile_pyc=True, pip_args=['numpy'])
    """

    if pip_args is None:
        pip_args = []

    if not pip_args and not site_packages:
        sys.exit(NO_PIP_ARGS_OR_SITE_PACKAGES)

    if output_file is None:
        sys.exit(NO_OUTFILE)

    # check for disallowed pip arguments
    for disallowed in DISALLOWED_ARGS:
        for supplied_arg in pip_args:
            if supplied_arg in disallowed:
                sys.exit(DISALLOWED_PIP_ARGS.format(arg=supplied_arg, reason=DISALLOWED_ARGS[disallowed]))

    if build_id is not None:
        click.secho(
            "Warning! You have overridden the default build-id behavior, "
            "executables created by shiv must have unique build IDs or unexpected behavior could occur.",
            fg="yellow",
        )

    sources: List[Path] = []

    with TemporaryDirectory() as tmp_site_packages:

        # If both site_packages and pip_args are present, we need to copy the site_packages
        # dir into our staging area (tmp_site_packages) as pip may modify the contents.
        if site_packages:
            if pip_args:
                for sp in site_packages:
                    copytree(Path(sp), Path(tmp_site_packages))
            else:
                sources.extend([Path(p).expanduser() for p in site_packages])

        if pip_args:
            # Install dependencies into staged site-packages.
            pip.install(["--target", tmp_site_packages] + list(pip_args))

        if preamble:
            bin_dir = Path(tmp_site_packages, "bin")
            bin_dir.mkdir(exist_ok=True)
            shutil.copy(Path(preamble).absolute(), bin_dir / Path(preamble).name)

        sources.append(Path(tmp_site_packages).absolute())

        if no_modify:
            # if no_modify is specified, we need to build a map of source files and their
            # sha256 hashes, to be checked at runtime:
            hashes = {}

            for source in sources:
                for path in source.rglob("**/*.py"):
                    hashes[str(path.relative_to(source))] = hashlib.sha256(path.read_bytes()).hexdigest()

        # if entry_point is a console script, get the callable and null out the console_script variable
        # so that we avoid modifying sys.argv in bootstrap.py
        if entry_point is None and console_script is not None:
            try:
                entry_point = find_entry_point(sources, console_script)
            except KeyError:
                if not console_script_exists(sources, console_script):
                    sys.exit(NO_ENTRY_POINT.format(entry_point=console_script))
            else:
                console_script = None

        # Some projects need reproducible artifacts, so they can use SOURCE_DATE_EPOCH
        # environment variable to specify the timestamps in the zipapp.
        timestamp = int(
            os.environ.get(SOURCE_DATE_EPOCH_ENV, SOURCE_DATE_EPOCH_DEFAULT if reproducible else time.time())
        )

        # create runtime environment metadata
        env = Environment(
            built_at=datetime.utcfromtimestamp(timestamp).strftime(BUILD_AT_TIMESTAMP_FORMAT),
            build_id=build_id,
            entry_point=entry_point,
            script=console_script,
            compile_pyc=compile_pyc,
            extend_pythonpath=extend_pythonpath,
            shiv_version=__version__,
            no_modify=no_modify,
            reproducible=reproducible,
            preamble=Path(preamble).name if preamble else None,
            root=root,
        )

        if no_modify:
            env.hashes = hashes

        # create the zip
        builder.create_archive(
            sources,
            target=Path(output_file).expanduser(),
            interpreter=python or DEFAULT_SHEBANG,
            main="_bootstrap:bootstrap",
            env=env,
            compressed=compressed,
        )


if __name__ == "__main__":  # pragma: no cover
    from shiv.commands import shiv
    shiv()
