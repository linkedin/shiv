import os
import shutil

import hashlib
import sys
import time

from configparser import ConfigParser
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Optional

import click

from . import builder, pip
from .bootstrap.environment import Environment
from .constants import (
    BUILD_AT_TIMESTAMP_FORMAT,
    DISALLOWED_ARGS,
    DISALLOWED_PIP_ARGS,
    NO_ENTRY_POINT,
    NO_OUTFILE,
    NO_PIP_ARGS_OR_SITE_PACKAGES,
    SOURCE_DATE_EPOCH_DEFAULT,
    SOURCE_DATE_EPOCH_ENV,
)

__version__ = "0.4.0"


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


def get_interpreter_path(append_version: bool = False) -> str:
    """A function to return the path to the current Python interpreter.

    Even when inside a venv, this will return the interpreter the venv was created with.

    """

    base_dir = Path(getattr(sys, "real_prefix", sys.base_prefix)).resolve()
    sys_exec = Path(sys.executable)
    name = sys_exec.stem
    suffix = sys_exec.suffix

    if append_version:
        name += str(sys.version_info.major)

    name += suffix

    try:
        return str(next(iter(base_dir.rglob(name))))

    except StopIteration:

        if not append_version:
            # If we couldn't find an interpreter, it's likely that we looked for
            # "python" when we should've been looking for "python3"
            # so we try again with append_version=True
            return get_interpreter_path(append_version=True)

        # If we were still unable to find a real interpreter for some reason
        # we fallback to the current runtime's interpreter
        return sys.executable


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


@click.command(context_settings=dict(help_option_names=["-h", "--help", "--halp"], ignore_unknown_options=True))
@click.version_option(version=__version__, prog_name="shiv")
@click.option(
    "--entry-point", "-e", default=None, help="The entry point to invoke (takes precedence over --console-script)."
)
@click.option("--console-script", "-c", default=None, help="The console_script to invoke.")
@click.option("--output-file", "-o", help="The path to the output file for shiv to create.")
@click.option("--python", "-p", help="The python interpreter to set as the shebang (such as '/usr/bin/env python3')")
@click.option(
    "--site-packages",
    help="The path to an existing site-packages directory to copy into the zipapp.",
    type=click.Path(exists=True),
    multiple=True,
)
@click.option("--compressed/--uncompressed", default=True, help="Whether or not to compress your zip.")
@click.option(
    "--compile-pyc", is_flag=True, help="Whether or not to compile pyc files during initial bootstrap.",
)
@click.option(
    "--extend-pythonpath", "-E", is_flag=True, help="Add the contents of the zipapp to PYTHONPATH (for subprocesses).",
)
@click.option(
    "--reproducible",
    is_flag=True,
    help=(
        "Generate a reproducible zipapp by overwriting all files timestamps to a default value. "
        "Timestamp can be overwritten by SOURCE_DATE_EPOCH env variable. "
        "Note: If SOURCE_DATE_EPOCH is set, this option will be implicitly set to true."
    ),
)
@click.option(
    "--no-modify",
    is_flag=True,
    help=(
        "If specified, this modifies the runtime of the zipapp to raise "
        "a RuntimeException if the source files (in ~/.shiv or SHIV_ROOT) have been modified. "
        """It's recommended to use Python's "--check-hash-based-pycs always" option with this feature."""
    ),
)
@click.option(
    "--preamble",
    type=click.Path(exists=True),
    help=(
        "Provide a path to a preamble script that is invoked by shiv's runtime after bootstrapping the environment, "
        "but before invoking your entry point."
    ),
)
@click.option("--root", type=click.Path(), help="Override the 'root' path (default is ~/.shiv).")
@click.argument("pip_args", nargs=-1, type=click.UNPROCESSED)
def main(
    output_file: str,
    entry_point: Optional[str],
    console_script: Optional[str],
    python: Optional[str],
    site_packages: Optional[str],
    compressed: bool,
    compile_pyc: bool,
    extend_pythonpath: bool,
    reproducible: bool,
    no_modify: bool,
    preamble: Optional[str],
    root: Optional[str],
    pip_args: List[str],
) -> None:
    """
    Shiv is a command line utility for building fully self-contained Python zipapps
    as outlined in PEP 441, but with all their dependencies included!
    """

    if not pip_args and not site_packages:
        sys.exit(NO_PIP_ARGS_OR_SITE_PACKAGES)

    if output_file is None:
        sys.exit(NO_OUTFILE)

    # check for disallowed pip arguments
    for disallowed in DISALLOWED_ARGS:
        for supplied_arg in pip_args:
            if supplied_arg in disallowed:
                sys.exit(DISALLOWED_PIP_ARGS.format(arg=supplied_arg, reason=DISALLOWED_ARGS[disallowed]))

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

        # if entry_point is a console script, get the callable
        if entry_point is None and console_script is not None:
            try:
                entry_point = find_entry_point(sources, console_script)
            except KeyError:
                if not console_script_exists(sources, console_script):
                    sys.exit(NO_ENTRY_POINT.format(entry_point=console_script))

        # Some projects need reproducible artifacts, so they can use SOURCE_DATE_EPOCH
        # environment variable to specify the timestamps in the zipapp.
        timestamp = int(
            os.environ.get(SOURCE_DATE_EPOCH_ENV, SOURCE_DATE_EPOCH_DEFAULT if reproducible else time.time())
        )

        # create runtime environment metadata
        env = Environment(
            built_at=datetime.utcfromtimestamp(timestamp).strftime(BUILD_AT_TIMESTAMP_FORMAT),
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
            interpreter=python or get_interpreter_path(),
            main="_bootstrap:bootstrap",
            env=env,
            compressed=compressed,
        )


if __name__ == "__main__":  # pragma: no cover
    main()
