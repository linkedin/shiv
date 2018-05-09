import contextlib
import os
import subprocess
import sys

from pathlib import Path
from typing import Generator, List

from .constants import PIP_REQUIRE_VIRTUALENV, PIP_INSTALL_ERROR, DISTUTILS_CFG_NO_PREFIX


@contextlib.contextmanager
def clean_pip_env() -> Generator[None, None, None]:
    """A context manager for temporarily removing 'PIP_REQUIRE_VIRTUALENV' from the environment.

    Since shiv installs via `--target`, we need to ignore venv requirements if they exist.

    """
    require_venv = os.environ.pop(PIP_REQUIRE_VIRTUALENV, None)

    distutils_cfg = Path.home() / ".pydistutils.cfg"
    distutils_cfg_already_existed = distutils_cfg.exists()
    if not distutils_cfg_already_existed:
        # distutils doesn't support using --target if there's a config file
        # specifying --prefix. Homebrew's Pythons include a distutils.cfg that
        # breaks `pip install --target` with any non-wheel packages. We can
        # work around that by creating a temporary ~/.pydistutils.cfg
        # specifying an empty prefix.
        distutils_cfg.write_text(DISTUTILS_CFG_NO_PREFIX)

    try:
        yield

    finally:
        if require_venv is not None:
            os.environ[PIP_REQUIRE_VIRTUALENV] = require_venv
        if not distutils_cfg_already_existed:
            # remove the temporary ~/.pydistutils.cfg
            distutils_cfg.unlink()


def install(interpreter_path: str, args: List[str]) -> None:
    """`pip install` as a function.

    Accepts a list of pip arguments.

    .. code-block:: py

        >>> install('/usr/local/bin/python3', ['numpy', '--target', 'site-packages'])
        Collecting numpy
        Downloading numpy-1.13.3-cp35-cp35m-manylinux1_x86_64.whl (16.9MB)
            100% || 16.9MB 53kB/s
        Installing collected packages: numpy
        Successfully installed numpy-1.13.3

    """
    with clean_pip_env():

        process = subprocess.Popen(
            [interpreter_path, "-m", "pip", "--disable-pip-version-check", "install"] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        for output in process.stdout:
            if output:
                print(output.decode().rstrip())

        if process.wait() > 0:
            sys.exit(PIP_INSTALL_ERROR)
