"""This module contains various error messages."""
from typing import Dict, Tuple

# errors:
DISALLOWED_PIP_ARGS = "\nYou supplied a disallowed pip argument! '{arg}'\n\n{reason}\n"
NO_PIP_ARGS_OR_SITE_PACKAGES = "\nYou must supply PIP ARGS or --site-packages!\n"
NO_OUTFILE = "\nYou must provide an output file option! (--output-file/-o)\n"
NO_ENTRY_POINT = "\nNo entry point '{entry_point}' found in console_scripts or the bin dir!\n"
BINPRM_ERROR = "\nShebang is too long, it would exceed BINPRM_BUF_SIZE! Consider /usr/bin/env\n"

# pip
PIP_INSTALL_ERROR = "\nPip install failed!\n"
PIP_REQUIRE_VIRTUALENV = "PIP_REQUIRE_VIRTUALENV"
DISALLOWED_ARGS: Dict[Tuple[str, ...], str] = {
    ("-t", "--target"): "Shiv already supplies a target internally, so overriding is not allowed.",
    (
        "--editable",
    ): "Editable installs don't actually install via pip (they are just linked), so they are not allowed.",
    ("-d", "--download"): "Shiv needs to actually perform an install, not merely a download.",
    ("--user", "--prefix"): "Which conflicts with Shiv's internal use of '--target'.",
}

SOURCE_DATE_EPOCH_ENV = "SOURCE_DATE_EPOCH"
# This is the timestamp for beginning of the day Jan 1 1980, which is the minimum timestamp
# value you can use in zip archives
SOURCE_DATE_EPOCH_DEFAULT = 315554400
BUILD_AT_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

# The default shebang to use at the top of the pyz.
# We use "/usr/bin/env" here because it's cross-platform compatible
# https://docs.python.org/3/using/windows.html#shebang-lines
DEFAULT_SHEBANG = "/usr/bin/env python3"
