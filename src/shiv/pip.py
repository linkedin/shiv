import contextlib
import os

from pip import check_isolated
from pip.commands.install import InstallCommand

from .constants import PIP_REQUIRE_VIRTUALENV


@contextlib.contextmanager
def clean_pip_env():
    """A context manager for temporarily removing 'PIP_REQUIRE_VIRTUALENV' from the environment.

    Since shiv installs via `--target`, we need to ignore venv requirements if they exist.

    """
    require_venv = os.environ.pop(PIP_REQUIRE_VIRTUALENV, None)
    try:
        yield
    finally:
        if require_venv is not None:
            os.environ[PIP_REQUIRE_VIRTUALENV] = require_venv


def install(args):
    """`pip install` as a function.

    Accepts a list of pip arguments.

    .. example::

        >>> install(['numpy', '--target', 'site-packages'])
        Collecting numpy
        Downloading numpy-1.13.3-cp35-cp35m-manylinux1_x86_64.whl (16.9MB)
            100% || 16.9MB 53kB/s
        Installing collected packages: numpy
        Successfully installed numpy-1.13.3

    """
    with clean_pip_env():
        cmd = InstallCommand(isolated=check_isolated(args))
        cmd.main(args)
