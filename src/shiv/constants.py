"""This module contains various error messages."""
from typing import Tuple, Dict

# errors:
DISALLOWED_PIP_ARGS = "\nYou supplied a disallowed pip argument! '{arg}'\n\n{reason}\n"
NO_PIP_ARGS = "\nYou must supply PIP ARGS!\n"
NO_OUTFILE = "\nYou must provide an output file option! (--output-file/-o)\n"
INVALID_PYTHON = "\nInvalid python interpreter! {path} does not exist!\n"
NO_ENTRY_POINT = "\nNo entry point '{entry_point}' found in the console_scripts!\n"
PIP_INSTALL_ERROR = "\nPip install failed!\n"

# pip
PIP_INSTALL_ERROR = "\nPip install failed!\n"
PIP_REQUIRE_VIRTUALENV = "PIP_REQUIRE_VIRTUALENV"
BLACKLISTED_ARGS: Dict[Tuple[str, ...], str] = {
    ("-t", "--target"): "Shiv already supplies a target internally, so overriding is not allowed.",
    ("--editable", ): "Editable installs don't actually install via pip (they are just linked), so they are not allowed.",
    ("-d", "--download"): "Shiv needs to actually perform an install, not merely a download.",
    ("--user", "--root", "--prefix"): "Which conflicts with Shiv's internal use of '--target'.",
}
DISTUTILS_CFG_NO_PREFIX = "[install]\nprefix="
