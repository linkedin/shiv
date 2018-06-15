"""This module contains various error messages."""
from typing import Dict, Set, Tuple

# errors:
DISALLOWED_PIP_ARGS = "\nYou supplied a disallowed pip argument! '{arg}'\n\n{reason}\n"
NO_PIP_ARGS = "\nYou must supply PIP ARGS!\n"
NO_OUTFILE = "\nYou must provide an output file option! (--output-file/-o)\n"
NO_ENTRY_POINT = "\nNo entry point '{entry_point}' found in the console_scripts!\n"
PIP_INSTALL_ERROR = "\nPip install failed!\n"
BINPRM_ERROR = "\nShebang is too long, it would exceed BINPRM_BUF_SIZE! Consider /usr/bin/env"
PIP_DOWNLOAD_ERROR = "\nPip download failed!\n"
PIP_WHEEL_ERROR = "\nPip wheel failed!\n"

# pip
PIP_REQUIRE_VIRTUALENV = "PIP_REQUIRE_VIRTUALENV"
BLACKLISTED_ARGS: Dict[Tuple[str, ...], str] = {
    ("-d", "--dest"): "Shiv already supplies a destination internally, so overriding is not allowed.",
    ("-w", "--wheel-dir"): "Shiv already supplies a wheel dir internally, so overriding is not allowed.",
}
DISTUTILS_CFG_NO_PREFIX = "[install]\nprefix="
