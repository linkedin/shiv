import shutil
import sys
import uuid

from configparser import ConfigParser
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Optional

import click

from . import builder, pip
from .bootstrap.environment import Environment
from .constants import DISALLOWED_ARGS, DISALLOWED_PIP_ARGS, NO_ENTRY_POINT, NO_OUTFILE, NO_PIP_ARGS_OR_SITE_PACKAGES

__version__ = "0.0.51"


def find_entry_point(site_packages: Path, console_script: str) -> str:
    """Find a console_script in a site-packages directory.

    Console script metadata is stored in entry_points.txt per setuptools
    convention. This function searches all entry_points.txt files and
    returns the import string for a given console_script argument.

    :param site_packages: A path to a site-packages directory on disk.
    :param console_script: A console_script string.
    """

    config_parser = ConfigParser()
    config_parser.read(site_packages.rglob("entry_points.txt"))
    return config_parser["console_scripts"][console_script]


def _interpreter_path(append_version: bool = False) -> str:
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
            return _interpreter_path(append_version=True)

        # If we were still unable to find a real interpreter for some reason
        # we fallback to the current runtime's interpreter
        return sys.executable


@click.command(context_settings=dict(help_option_names=["-h", "--help", "--halp"], ignore_unknown_options=True))
@click.version_option(version=__version__, prog_name="shiv")
@click.option("--entry-point", "-e", default=None, help="The entry point to invoke.")
@click.option("--console-script", "-c", default=None, help="The console_script to invoke.")
@click.option("--output-file", "-o", help="The file for shiv to create.")
@click.option("--python", "-p", help="The path to a python interpreter to use.")
@click.option(
    "--site-packages",
    help="The path to an existing site-packages directory to copy into the zipapp",
    type=click.Path(exists=True),
)
@click.option("--compressed/--uncompressed", default=True, help="Whether or not to compress your zip.")
@click.option(
    "--compile-pyc/--no-compile-pyc",
    default=False,
    help="Whether or not to compile pyc files during initial bootstrap.",
)
@click.option(
    "--extend-pythonpath/--no-extend-pythonpath",
    "-E",
    default=False,
    help="Add the contents of the zipapp to PYTHONPATH (for subprocesses).",
)
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

    with TemporaryDirectory() as tmp_site_packages:

        # If both site_packages and pip_args are present, we need to copy the site_packages
        # dir into our staging area (tmp_site_packages) as pip may modify the contents.
        if site_packages:
            if pip_args:
                shutil.copytree(site_packages, tmp_site_packages)
            else:
                tmp_site_packages = site_packages

        if pip_args:
            # Install dependencies into staged site-packages.
            pip.install(["--target", tmp_site_packages] + list(pip_args))

        # if entry_point is a console script, get the callable
        if entry_point is None and console_script is not None:
            try:
                entry_point = find_entry_point(Path(tmp_site_packages), console_script)

            except KeyError:
                if not Path(tmp_site_packages, "bin", console_script).exists():
                    sys.exit(NO_ENTRY_POINT.format(entry_point=console_script))

        # create runtime environment metadata
        env = Environment(
            built_at=str(datetime.now()),
            build_id=str(uuid.uuid4()),
            entry_point=entry_point,
            script=console_script,
            compile_pyc=compile_pyc,
            extend_pythonpath=extend_pythonpath,
            shiv_version=__version__,
        )

        # create the zip
        builder.create_archive(
            Path(tmp_site_packages).expanduser(),
            target=Path(output_file).expanduser(),
            interpreter=python or _interpreter_path(),
            main="_bootstrap:bootstrap",
            env=env,
            compressed=compressed,
        )


if __name__ == "__main__":
    main()  # pragma: no cover
