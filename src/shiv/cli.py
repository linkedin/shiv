import importlib_resources  # type: ignore
import os
import shutil
import sys
import uuid

from configparser import ConfigParser
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, Optional, List

import click

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
    INVALID_PYTHON,
)

# This is the 'knife' emoji
SHIV = u'\U0001F52A'


def find_entry_point(site_packages: Path, console_script: str) -> str:
    """Find a console_script in a site-packages directory.

    Console script metadata is stored in entry_points.txt per setuptools
    convention. This function searches all entry_points.txt files and
    returns the import string for a given console_script argument.

    :param site_packages: A path to a site-packages directory on disk.
    :param console_script: A console_script string.
    """
    config_parser = ConfigParser()
    config_parser.read(site_packages.rglob('entry_points.txt'))
    return config_parser['console_scripts'][console_script]


def validate_interpreter(interpreter_path: Optional[str] = None) -> Path:
    """Ensure that the interpreter is a real path, not a symlink.

    If no interpreter is given, default to `sys.exectuable`

    :param interpreter_path: A path to a Python interpreter.
    """
    real_path = Path(sys.executable) if interpreter_path is None else Path(interpreter_path)

    if real_path.exists():
        return real_path
    else:
        sys.exit(INVALID_PYTHON.format(path=real_path))


def map_shared_objects(site_packages: Path) -> Dict[str, str]:
    """Given a site-packages dir, map all of the shared objects to their namespaces.

    :param site_packages: A path to a custom site-packages directory.
    """
    somap: Dict[str, str] = {}

    for parent_dir, _, filenames in os.walk(site_packages):
        for filename in filenames:

            # get full path to file
            fullpath = Path(parent_dir) / filename

            # check if the file is a shared object (skipping if not)
            if fullpath.suffix not in ['.so', '.dylib']:
                continue

            # assemble the mapping of import path to file
            index = fullpath.parts.index('site-packages') + 1
            contributors = list(fullpath.parts[index:-1])
            module_name, import_tag, extension = fullpath.parts[-1].split('.')
            contributors.append(module_name)
            import_path = '.'.join(contributors)

            # finally, add the import path to the shared object map
            somap[import_path] = fullpath.relative_to(site_packages).as_posix()

    return somap


def copy_bootstrap(bootstrap_target: Path) -> None:
    """Copy bootstrap code from shiv into the pyz.

    First check if this instance of shiv is in fact already a (zip-safe) zipapp, and then
    copy the bootstrap files over accordingly.

    :param bootstrap_target: The temporary directory where we are staging pyz contents.
    """
    for bootstrap_file in importlib_resources.contents(bootstrap):
        if importlib_resources.is_resource(bootstrap, bootstrap_file):
            with importlib_resources.path(bootstrap, bootstrap_file) as f:
                shutil.copyfile(f.absolute(), bootstrap_target / f.name)


@click.command(context_settings=dict(help_option_names=['-h', '--help'], ignore_unknown_options=True))
@click.option('--entry-point', '-e', default=None, help='the entry point to bake into your executable')
@click.option('--console-script', '-c', default=None, help='the console_script to bake into your executable')
@click.option('--output-file', '-o', help='the file for shiv to create')
@click.option('--python', '-p', help='path to your python interpreter')
@click.option('--zip-safe/--not-zip-safe', default=False, help='whether or not your shiv-file is zip-safe')
@click.option('--compressed/--uncompressed', default=True, help='whether or not to compress your zip')
@click.argument('pip_args', nargs=-1, type=click.UNPROCESSED)
def main(
    output_file: str,
    entry_point: Optional[str],
    console_script: Optional[str],
    python: Optional[str],
    zip_safe: bool,
    compressed: bool,
    pip_args: List[str],
) -> None:
    """ Shiv creates python executables! """
    quiet = '-q' in pip_args

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
                        arg=supplied_arg,
                        reason=BLACKLISTED_ARGS[blacklisted_arg],
                    )
                )

    # validate supplied python (if any)
    interpreter = validate_interpreter(python)

    with TemporaryDirectory() as working_path:
        site_packages = Path(working_path, 'site-packages')
        site_packages.mkdir(parents=True, exist_ok=True)

        # install deps into staged site-packages
        pip.install(python or sys.executable, ['--target', site_packages.as_posix()] + list(pip_args))

        # if entry_point is a console script, get the callable
        if entry_point is None and console_script is not None:
            try:
                entry_point = find_entry_point(site_packages, console_script)
            except KeyError:
                sys.exit(NO_ENTRY_POINT.format(entry_point=console_script))

        # create runtime environment metadata
        env = Environment(
            build_id=str(uuid.uuid4()),
            zip_safe=zip_safe,
            entry_point=entry_point,
            shared_object_map=map_shared_objects(Path(working_path)),
        )

        Path(working_path, 'environment.json').write_text(env.to_json())

        # create bootstrapping directory in working path
        bootstrap_target = Path(working_path, '_bootstrap')
        bootstrap_target.mkdir(parents=True, exist_ok=True)

        # copy bootstrap code
        copy_bootstrap(bootstrap_target)

        # create the zip
        builder.create_archive(
            Path(working_path),
            target=Path(output_file),
            interpreter=interpreter,
            main='_bootstrap:bootstrap',
            compressed=compressed,
        )

    if not quiet:
        click.secho(" done ", bold=True)
