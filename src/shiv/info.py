import click
import json
import zipfile


def write_info(print_as_json: bool, pyz: str):
    """print debugging information about the PYZ file passed in """

    zip_file = zipfile.ZipFile(pyz)
    data = json.loads(zip_file.read("environment.json"))

    if print_as_json:
        click.echo(json.dumps(data, indent=4, sort_keys=True))

    else:
        click.echo()
        click.secho(f"pyz file: ", fg="green", bold=True, nl=False)
        click.secho(pyz, fg="white")
        click.echo()

        for key, value in data.items():
            click.secho(f"{key}: ", fg="blue", bold=True, nl=False)
            click.secho(f"{value}", fg="white")

        click.echo()


@click.command(context_settings=dict(help_option_names=["-h", "--help", "--halp"]))
@click.option("--json", "-j", "print_as_json", is_flag=True, help="output as plain json")
@click.argument("pyz")
def main(print_as_json, pyz):
    """A simple utility to print debugging information about PYZ files created with ``shiv``"""

    write_info(print_as_json, pyz)
