import json
import click
import zipfile

from shiv.cli import __version__
from shiv.cli import main as shiv_main


# FIXME these options' required and default values need to be kept in sync with
# shiv.cli.main, but could be inferred from its kwarg annotations on Python >3.10
@click.command(context_settings=dict(help_option_names=["-h", "--help", "--halp"], ignore_unknown_options=True))
@click.version_option(version=__version__, prog_name="shiv")
@click.option(
    "--entry-point", "-e", default=None, help="The entry point to invoke (takes precedence over --console-script)."
)
@click.option("--console-script", "-c", default=None, help="The console_script to invoke.")
@click.option("--output-file", "-o", help="The path to the output file for shiv to create.")
@click.option(
    "--python",
    "-p",
    help=(
        "The python interpreter to set as the shebang, a.k.a. whatever you want after '#!' "
        "(default is '/usr/bin/env python3')"
    ),
)
@click.option(
    "--site-packages",
    help="The path to an existing site-packages directory to copy into the zipapp.",
    type=click.Path(exists=True),
    multiple=True,
)
@click.option(
    "--build-id",
    default=None,
    help=(
        "Use a custom build id instead of the default (a SHA256 hash of the contents of the build). "
        "Warning: must be unique per build!"
    ),
)
@click.option("--compressed/--uncompressed", default=True, help="Whether or not to compress your zip.")
@click.option(
    "--compile-pyc",
    is_flag=True,
    help="Whether or not to compile pyc files during initial bootstrap.",
)
@click.option(
    "--extend-pythonpath",
    "-E",
    is_flag=True,
    help="Add the contents of the zipapp to PYTHONPATH (for subprocesses).",
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
def shiv(**kwargs):
    """
    Shiv is a command line utility for building fully self-contained Python zipapps
    as outlined in PEP 441, but with all their dependencies included!
    """
    shiv_main(**kwargs)


@click.command(context_settings=dict(help_option_names=["-h", "--help", "--halp"]))
@click.option("--json", "-j", "print_as_json", is_flag=True, help="output as plain json")
@click.argument("pyz")
def shiv_info(print_as_json, pyz):
    """A simple utility to print debugging information about PYZ files created with ``shiv``"""

    zip_file = zipfile.ZipFile(pyz)
    data = json.loads(zip_file.read("environment.json"))

    if print_as_json:
        click.echo(json.dumps(data, indent=4, sort_keys=True))

    else:
        click.echo()
        click.secho("pyz file: ", fg="green", bold=True, nl=False)
        click.secho(pyz, fg="white")
        click.echo()

        for key, value in data.items():
            click.secho(f"{key}: ", fg="blue", bold=True, nl=False)

            if key == "hashes":
                click.secho(json.dumps(value, sort_keys=True, indent=2))
            else:
                click.secho(f"{value}", fg="white")

        click.echo()
