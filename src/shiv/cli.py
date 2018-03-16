import os
import shutil
import sys
import uuid

from configparser import ConfigParser
from pathlib import Path
from tempfile import TemporaryDirectory

import click

from . import pip
from . import builder
from . import bootstrap
from .bootstrap.environment import Environment
from .bootstrap.utils import current_zipfile, loaded_from_zipfile
from .constants import (
    BLACKLISTED_ARGS,
    DISALLOWED_PIP_ARGS,
    NO_PIP_ARGS,
    NO_OUTFILE,
    NO_ENTRY_POINT,
    PY_SUFFIX,
    INVALID_PYTHON,
)

# This is the 'knife' emoji
SHIV = u'\U0001F52A'

# Typical maximum length for a shebang line
BINPRM_BUF_SIZE = 128


def find_entry_point(site_packages, console_script):
    """Find a console_script in a site-packages directory.

    Console script metadata is stored in entry_points.txt per setuptools
    convention. This function searches all entry_points.txt files and
    returns the import string for a given console_script argument.

    :param Path site_packages: A path to a site-packages directory on disk.
    :param str console_script: A console_script string.
    """
    config_parser = ConfigParser()
    config_parser.read(site_packages.rglob('entry_points.txt'))
    return config_parser['console_scripts'][console_script]


def validate_interpreter(interpreter_path=None):
    """Ensure that the interpreter is a real path, not a symlink.

    If no interpreter is given, default to `sys.exectuable`

    :param Path interpreter_path: A path to a Python interpreter.
    """
    real_path = Path(sys.executable if interpreter_path is None else interpreter_path)

    # fall back to /usr/bin/env if the interp path is too long
    if interpreter_path is None or len(real_path.as_posix()) > BINPRM_BUF_SIZE:
        return f'/usr/bin/env {real_path.name}'

    if real_path.exists():
        return real_path.as_posix()
    else:
        sys.exit(INVALID_PYTHON.format(path=real_path))


def map_shared_objects(site_packages):
    """Given a site-packages dir, map all of the shared objects to their namespaces.

    :param Path site_packages: A path to a custom site-packages directory.
    """
    somap = {}

    for dirpath, dirnames, filenames in os.walk(site_packages):
        for filename in filenames:
            fullpath = Path(dirpath) / Path(filename)
            if fullpath.suffix not in ['.so', '.dylib']:
                continue
            index = fullpath.parts.index('site-packages') + 1
            contributors = list(fullpath.parts[index:-1])
            module_name, import_tag, extension = fullpath.parts[-1].split('.')
            contributors.append(module_name)
            import_path = '.'.join(contributors)
            somap[import_path] = str(fullpath.relative_to(site_packages))

    return somap


def copy_bootstrap(bootstrap_target):
    """Copy bootstrap code from shiv into the pyz.

    First check if this instance of shiv is in fact already a (zip-safe) zipapp, and then
    copy the bootstrap files over accordingly.

    TODO: use importlib.resources for this!

    :param Path bootstrap_target: The temporary directory where we are staging pyz contents.
    """
    if loaded_from_zipfile(bootstrap):
        archive = current_zipfile()
        bootstrap_zip_root = str(
            Path(bootstrap.__file__).relative_to(Path(archive.filename)).parent
        )
        for f in [Path(f) for f in archive.namelist() if f.startswith(bootstrap_zip_root)]:
            if f.suffix == PY_SUFFIX:
                with TemporaryDirectory() as zip_move_dir:
                    archive.extract(str(f), zip_move_dir)
                    shutil.move(Path(zip_move_dir, f), Path(bootstrap_target, f.name))
    else:
        bootstrap_src = Path(bootstrap.__file__).absolute().parent
        for f in bootstrap_src.iterdir():
            if f.suffix == PY_SUFFIX:
                shutil.copyfile(f.absolute(), Path(bootstrap_target, f.name))


@click.command(context_settings=dict(help_option_names=['-h', '--help'], ignore_unknown_options=True))
@click.option('--entry-point', '-e', default=None, help='the entry point to bake into your executable')
@click.option('--console-script', '-c', default=None, help='the console_script to bake into your executable')
@click.option('--output-file', '-o', help='the file for shiv to create')
@click.option('--python', '-p', help='path to your python interpreter')
@click.option('--zip-safe/--not-zip-safe', default=False, help='whether or not your shiv-file is zip-safe')
@click.option('--compressed/--uncompressed', default=True, help='whether or not to compress your zip')
@click.argument('pip_args', nargs=-1, type=click.UNPROCESSED)
def main(
    output_file,
    entry_point,
    console_script,
    python,
    zip_safe,
    compressed,
    pip_args,
):
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
    python = validate_interpreter(python)

    with TemporaryDirectory() as working_path:
        site_packages = Path(working_path, 'site-packages')
        site_packages.mkdir(parents=True, exist_ok=True)

        # install deps into staged site-packages
        pip.install(['--target', site_packages] + list(pip_args))

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
            shared_object_map=map_shared_objects(working_path),
        )

        Path(working_path, 'environment.json').write_text(env.to_json())

        # create bootstrapping directory in working path
        bootstrap_target = Path(working_path, '_bootstrap')
        bootstrap_target.mkdir(parents=True, exist_ok=True)

        # copy bootstrap code
        copy_bootstrap(bootstrap_target)

        # create the zip
        builder.create_archive(
            working_path,
            target=output_file,
            interpreter=python,
            main='_bootstrap:bootstrap',
            compressed=compressed,
        )

    if not quiet:
        click.secho(" done ", bold=True)
