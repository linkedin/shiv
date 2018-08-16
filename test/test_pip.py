import os

from shiv.constants import PIP_REQUIRE_VIRTUALENV
from shiv.pip import clean_pip_env


def test_clean_pip_env(monkeypatch):

    before_env_var = 'test'
    monkeypatch.setenv(PIP_REQUIRE_VIRTUALENV, before_env_var)

    with clean_pip_env():
        assert PIP_REQUIRE_VIRTUALENV not in os.environ

    assert os.environ.get(PIP_REQUIRE_VIRTUALENV) == before_env_var
