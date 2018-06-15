import importlib_resources  # type: ignore
import os
import shutil
import sys
import uuid

from collections import defaultdict
from configparser import ConfigParser
from itertools import chain
from pathlib import Path
from shutil import rmtree
from tempfile import TemporaryDirectory
from typing import Optional, List

import click

from wheel.install import WheelFile

from . import pip
from . import builder
from . import bootstrap
from .bootstrap.environment import Environment
from .constants import (
    BLACKLISTED_ARGS,
    DISALLOWED_PIP_ARGS,
    NO_PIP_ARGS,
    NO_OUTFILE,
    NO_ENTRY_POINT,
)

__version__ = '0.0.27'

# This is the 'knife' emoji
SHIV = u"\U0001F52A"


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


def copy_bootstrap(bootstrap_target: Path) -> None:
    """Copy bootstrap code from shiv into the pyz.

    :param bootstrap_target: The temporary directory where we are staging pyz contents.
    """
    for bootstrap_file in importlib_resources.contents(bootstrap):
        if importlib_resources.is_resource(bootstrap, bootstrap_file):
            with importlib_resources.path(bootstrap, bootstrap_file) as f:
                shutil.copyfile(f.absolute(), bootstrap_target / f.name)


def install_wheels(wheel_dir: Path, site_packages: Path) -> None:
    """Install wheels from wheel_dir into site_packages"""
    to_install = [WheelFile(req) for req in wheel_dir.glob('*.whl')]

    # We now have a list of wheels to install
    print("Installing:")

    # Ensure we always put stuff in site-packages no matter what
    overrides = {
        'purelib': str(site_packages),
        'platlib': str(site_packages),
        'headers': str(Path(site_packages, '..', 'headers')),
        'scripts': str(Path(site_packages, '..', 'scripts')),
        'data': str(Path(site_packages, '..', 'data')),
    }
    for wf in to_install:
        print("    {}".format(wf.filename))
        wf.install(force=True, overrides=overrides)
        wf.zipfile.close()


def build_wheels(wheel_dir: Path) -> None:
    """Build wheels for source packages in wheel_dir"""
    to_build = [str(path) for path in chain(wheel_dir.glob('*.tar.*'),
                                            wheel_dir.glob('*.zip'),
                                            wheel_dir.glob('*.tar'))]

    # build missing wheels
    if to_build:
        pip.wheel(
            ["--wheel-dir", str(wheel_dir), '--find-links', str(wheel_dir)] + to_build,
        )

    # remove source packages
    for sdist in to_build:
        os.unlink(sdist)


@click.command(
    context_settings=dict(
        help_option_names=["-h", "--help", "--halp"], ignore_unknown_options=True
    )
)
@click.version_option(version=__version__, prog_name='shiv')
@click.option("--entry-point", "-e", default=None, help="The entry point to invoke.")
@click.option(
    "--console-script", "-c", default=None, help="The console_script to invoke."
)
@click.option("--output-file", "-o", help="The file for shiv to create.")
@click.option("--python", "-p", help="The path to a python interpreter to use.")
@click.option(
    "--compressed/--uncompressed",
    default=True,
    help="Whether or not to compress your zip.",
)
@click.argument("pip_args", nargs=-1, type=click.UNPROCESSED)
def main(
    output_file: str,
    entry_point: Optional[str],
    console_script: Optional[str],
    python: Optional[str],
    compressed: bool,
    pip_args: List[str],
) -> None:
    """
    Shiv is a command line utility for building fully self-contained Python zipapps
    as outlined in PEP 441, but with all their dependencies included!
    """
    quiet = "-q" in pip_args or '--quiet' in pip_args

    if not quiet:
        click.secho(" shiv! " + SHIV, bold=True)

    if not pip_args:
        sys.exit(NO_PIP_ARGS)

    if output_file is None:
        sys.exit(NO_OUTFILE)

    # check for disallowed pip arguments
    for blacklisted_arg in BLACKLISTED_ARGS:
        for supplied_arg in pip_args:
            if supplied_arg in blacklisted_arg:
                sys.exit(
                    DISALLOWED_PIP_ARGS.format(
                        arg=supplied_arg, reason=BLACKLISTED_ARGS[blacklisted_arg]
                    )
                )

    with TemporaryDirectory() as working_path:
        wheel_dir = Path(working_path, "wheelhouse")
        wheel_dir.mkdir(parents=True, exist_ok=True)

        site_packages = Path(working_path, "site-packages")
        site_packages.mkdir(parents=True, exist_ok=True)

        # download wheels and sdists into wheel_dir
        pip.download(
            ["--dest", str(wheel_dir)] + list(pip_args),
        )

        # build missing wheels
        build_wheels(wheel_dir)

        # install deps into staged site-packages
        install_wheels(wheel_dir, site_packages)

        # remove wheel dir
        rmtree(str(wheel_dir))

        # if entry_point is a console script, get the callable
        if entry_point is None and console_script is not None:
            try:
                entry_point = find_entry_point(site_packages, console_script)
            except KeyError:
                sys.exit(NO_ENTRY_POINT.format(entry_point=console_script))

        # create runtime environment metadata
        env = Environment(
            build_id=str(uuid.uuid4()),
            entry_point=entry_point,
        )

        Path(working_path, "environment.json").write_text(env.to_json())

        # create bootstrapping directory in working path
        bootstrap_target = Path(working_path, "_bootstrap")
        bootstrap_target.mkdir(parents=True, exist_ok=True)

        # copy bootstrap code
        copy_bootstrap(bootstrap_target)

        # create the zip
        builder.create_archive(
            Path(working_path),
            target=Path(output_file),
            interpreter=python or sys.executable,
            main="_bootstrap:bootstrap",
            compressed=compressed,
        )

    if not quiet:
        click.secho(" done ", bold=True)
