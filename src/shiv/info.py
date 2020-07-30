import json
import zipfile

import click


@click.command(context_settings=dict(help_option_names=["-h", "--help", "--halp"]))
@click.option("--json", "-j", "print_as_json", is_flag=True, help="output as plain json")
@click.argument("pyz")
def main(print_as_json, pyz):
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
