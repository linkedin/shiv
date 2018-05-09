import os

from pathlib import Path

import pytest

from shiv.constants import PIP_REQUIRE_VIRTUALENV, DISTUTILS_CFG_NO_PREFIX
from shiv.pip import clean_pip_env


@pytest.mark.parametrize("distutils_cfg_exists", [True, False])
def test_clean_pip_env(monkeypatch, tmpdir, distutils_cfg_exists):
    home = tmpdir.join("home").ensure(dir=True)
    monkeypatch.setenv("HOME", home)

    distutils_cfg = Path(home) / ".pydistutils.cfg"

    if distutils_cfg_exists:
        distutils_contents = "foobar"
        distutils_cfg.write_text(distutils_contents)
    else:
        distutils_contents = None

    before_env_var = "foo"
    monkeypatch.setenv(PIP_REQUIRE_VIRTUALENV, before_env_var)

    with clean_pip_env():
        assert PIP_REQUIRE_VIRTUALENV not in os.environ

        if not distutils_cfg_exists:
            # ~/.pydistutils.cfg was created
            assert distutils_cfg.read_text() == DISTUTILS_CFG_NO_PREFIX
        else:
            # ~/.pydistutils.cfg was not modified
            assert distutils_cfg.read_text() == distutils_contents

    assert os.environ.get(PIP_REQUIRE_VIRTUALENV) == before_env_var

    # If a temporary ~/.pydistutils.cfg was created, it was deleted. If
    # ~/.pydistutils.cfg already existed, it still exists.
    assert distutils_cfg.exists() == distutils_cfg_exists
