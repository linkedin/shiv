import os

from pathlib import Path

import pytest

from shiv.constants import PIP_REQUIRE_VIRTUALENV, DISTUTILS_CFG_NO_PREFIX
from shiv.pip import clean_pip_env


@pytest.mark.parametrize("pydistutils_exists", ["pydistutils.cfg", ".pydistutils.cfg", None])
def test_clean_pip_env(monkeypatch, tmpdir, pydistutils_exists):
    home = tmpdir.join("home").ensure(dir=True)
    monkeypatch.setenv("HOME", home)

    if pydistutils_exists:
        pydistutils = Path.home() / pydistutils_exists
        pydistutils_contents = "foobar"
        pydistutils.write_text(pydistutils_contents)
    else:
        pydistutils = Path.home() / ".pydistutils.cfg"
        pydistutils_contents = None

    before_env_var = "foo"
    monkeypatch.setenv(PIP_REQUIRE_VIRTUALENV, before_env_var)

    with clean_pip_env():
        assert PIP_REQUIRE_VIRTUALENV not in os.environ

        if not pydistutils_exists:
            # ~/.pydistutils.cfg was created
            assert pydistutils.read_text() == DISTUTILS_CFG_NO_PREFIX
        else:
            # ~/.pydistutils.cfg was not modified
            assert pydistutils.read_text() == pydistutils_contents

    assert os.environ.get(PIP_REQUIRE_VIRTUALENV) == before_env_var

    # If a temporary ~/.pydistutils.cfg was created, it was deleted. If
    # ~/.pydistutils.cfg already existed, it still exists.
    assert pydistutils.exists() == bool(pydistutils_exists)
