"""This module contains various error messages."""
from typing import Tuple, Dict

# errors:
DISALLOWED_PIP_ARGS = "\nYou supplied a disallowed pip argument! '{arg}'\n\n{reason}\n"
NO_PIP_ARGS_OR_SITE_PACKAGES = "\nYou must supply PIP ARGS or --site-packages!\n"
NO_OUTFILE = "\nYou must provide an output file option! (--output-file/-o)\n"
NO_ENTRY_POINT = "\nNo entry point '{entry_point}' found in the console_scripts!\n"
PIP_INSTALL_ERROR = "\nPip install failed!\n"
BINPRM_ERROR = "\nShebang is too long, it would exceed BINPRM_BUF_SIZE! Consider /usr/bin/env"

# pip
PIP_INSTALL_ERROR = "\nPip install failed!\n"
PIP_REQUIRE_VIRTUALENV = "PIP_REQUIRE_VIRTUALENV"
BLACKLISTED_ARGS: Dict[Tuple[str, ...], str] = {
    ("-t", "--target"): "Shiv already supplies a target internally, so overriding is not allowed.",
    ("--editable", ): "Editable installs don't actually install via pip (they are just linked), so they are not allowed.",
    ("-d", "--download"): "Shiv needs to actually perform an install, not merely a download.",
    ("--user", "--root", "--prefix"): "Which conflicts with Shiv's internal use of '--target'.",
}
