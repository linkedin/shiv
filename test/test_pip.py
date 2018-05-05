import os

from pathlib import Path

from shiv.constants import PIP_REQUIRE_VIRTUALENV
from shiv.constants import SETUP_CFG_NO_PREFIX
from shiv.pip import clean_pip_env


def test_clean_pip_env(monkeypatch):
    before_env_var = 'foo'
    monkeypatch.setenv(PIP_REQUIRE_VIRTUALENV, before_env_var)

    before_cwd = Path.cwd()

    with clean_pip_env():
        assert PIP_REQUIRE_VIRTUALENV not in os.environ

        cwd = Path.cwd()
        assert cwd != before_cwd

        with cwd.joinpath("setup.cfg").open() as f:
            assert f.read() == SETUP_CFG_NO_PREFIX

    assert os.environ.get(PIP_REQUIRE_VIRTUALENV) == before_env_var
    assert Path.cwd() == before_cwd
