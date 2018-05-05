import os

from pathlib import Path

from shiv.constants import PIP_REQUIRE_VIRTUALENV
from shiv.constants import SETUP_CFG_NO_PREFIX
from shiv.pip import clean_pip_env


def test_clean_pip_env(monkeypatch):
    before_env_var = 'foo'
    monkeypatch.setenv(PIP_REQUIRE_VIRTUALENV, before_env_var)

    with clean_pip_env():
        assert PIP_REQUIRE_VIRTUALENV not in os.environ

        with Path(Path.cwd(), "setup.cfg").open() as f:
            assert f.read() == SETUP_CFG_NO_PREFIX

    assert os.environ.get(PIP_REQUIRE_VIRTUALENV) == before_env_var
