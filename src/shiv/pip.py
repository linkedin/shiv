import contextlib
import os
import subprocess
import sys

from pathlib import Path
from typing import Generator, List

from .constants import PIP_REQUIRE_VIRTUALENV, PIP_DOWNLOAD_ERROR, PIP_WHEEL_ERROR, DISTUTILS_CFG_NO_PREFIX


@contextlib.contextmanager
def clean_pip_env() -> Generator[None, None, None]:
    """A context manager for temporarily removing 'PIP_REQUIRE_VIRTUALENV' from the environment.

    Since shiv installs via `--target`, we need to ignore venv requirements if they exist.

    """
    require_venv = os.environ.pop(PIP_REQUIRE_VIRTUALENV, None)

    # https://github.com/python/cpython/blob/master/Lib/distutils/dist.py#L333-L363
    pydistutils = Path.home() / (".pydistutils.cfg" if os.name == "posix" else "pydistutils.cfg")
    pydistutils_already_existed = pydistutils.exists()

    if not pydistutils_already_existed:
        # distutils doesn't support using --target if there's a config file
        # specifying --prefix. Homebrew's Pythons include a distutils.cfg that
        # breaks `pip install --target` with any non-wheel packages. We can
        # work around that by creating a temporary ~/.pydistutils.cfg
        # specifying an empty prefix.
        pydistutils.write_text(DISTUTILS_CFG_NO_PREFIX)

    try:
        yield

    finally:
        if require_venv is not None:
            os.environ[PIP_REQUIRE_VIRTUALENV] = require_venv

        if not pydistutils_already_existed:
            # remove the temporary ~/.pydistutils.cfg
            pydistutils.unlink()


def download(args: List[str]) -> None:
    """`pip download` as a function.

    Accepts a list of pip arguments.

    .. code-block:: py

        >>> download(['numpy', '--dest', 'site-packages'])
        Collecting numpy
        Downloading numpy-1.13.3-cp35-cp35m-manylinux1_x86_64.whl (16.9MB)
            100% || 16.9MB 53kB/s
    """
    with clean_pip_env():

        process = subprocess.Popen(
            [sys.executable, "-m", "pip", "--disable-pip-version-check", "download"] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        for output in process.stdout:
            if output:
                print(output.decode().rstrip())

        if process.wait() > 0:
            sys.exit(PIP_DOWNLOAD_ERROR)


def wheel(args: List[str]) -> None:
    """`pip wheel` as a function.

    Accepts a list of pip arguments.

    .. code-block:: py

        >>> wheel(['numpy', '--wheel-dir', 'site-packages'])
        Collecting numpy
        Downloading https://files.pythonhosted.org/packages/8e/75/7a8b7e3c073562563473f2a61bd53e75d0a1f5e2047e576ee61d44113c22/numpy-1.14.3-cp36-cp36m-macosx_10_6_intel.macosx_10_9_intel.macosx_10_9_x86_64.macosx_10_10_intel.macosx_10_10_x86_64.whl (4.7MB)
        Saved ./site-packages/numpy-1.14.3-cp36-cp36m-macosx_10_6_intel.macosx_10_9_intel.macosx_10_9_x86_64.macosx_10_10_intel.macosx_10_10_x86_64.whl
        Skipping numpy, due to already being wheel.
    """
    with clean_pip_env():

        process = subprocess.Popen(
            [sys.executable, "-m", "pip", "--disable-pip-version-check", "wheel"] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        for output in process.stdout:
            if output:
                print(output.decode().rstrip())

        if process.wait() > 0:
            sys.exit(PIP_WHEEL_ERROR)
