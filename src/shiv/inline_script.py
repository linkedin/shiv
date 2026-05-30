import re
try:
    # python 3.11+ has tomllib in stdlib
    import tomllib  # type: ignore
except (ModuleNotFoundError, ImportError):
    # python 3.8-3.10, use pip vendored tomli
    import pip._vendor.tomli as tomllib  # type: ignore

REGEX = r'(?m)^# /// (?P<type>[a-zA-Z0-9-]+)$\s(?P<content>(^#(| .*)$\s)+)^# ///$'


def parse_script_metadata(script: str) -> dict:
    """Parses the metadata from a PEP-723 annotated script.

    The metadata is stored in a nested dictionary structure.
    The only PEP defined metadata type is "script", which contains the
    dependencies of the script and minimum Python version.

    :param script: The text of the script to parse.
    """

    metadata = {}

    for match in re.finditer(REGEX, script):
        md_type, content = match.group('type'), ''.join(
            line[2:] if line.startswith('# ') else line[1:]
            for line in match.group('content').splitlines(keepends=True)
        )
        metadata[md_type] = tomllib.loads(content)

    return metadata
