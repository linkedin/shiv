import os

from pathlib import Path

import pytest

from shiv.constants import PIP_REQUIRE_VIRTUALENV, DISTUTILS_CFG_NO_PREFIX
from shiv.pip import clean_pip_env


@pytest.mark.parametrize("pydistutils_path, os_name", [
    ("pydistutils.cfg", "nt"),
    (".pydistutils.cfg", "posix"),
    (None, os.name),
])
def test_clean_pip_env(monkeypatch, tmpdir, pydistutils_path, os_name):
    home = tmpdir.join("home").ensure(dir=True)
    monkeypatch.setenv("HOME", home)

    # patch os.name so distutils will use `pydistutils_path` for its config
    monkeypatch.setattr(os, 'name', os.name)

    if pydistutils_path:
        pydistutils = Path.home() / pydistutils_path
        pydistutils_contents = "foobar"
        pydistutils.write_text(pydistutils_contents)
    else:
        pydistutils = Path.home() / (
            ".pydistutils.cfg" if os.name == "posix" else "pydistutils.cfg"
        )
        pydistutils_contents = None

    before_env_var = "foo"
    monkeypatch.setenv(PIP_REQUIRE_VIRTUALENV, before_env_var)

    with clean_pip_env():
        assert PIP_REQUIRE_VIRTUALENV not in os.environ

        if not pydistutils_path:
            # ~/.pydistutils.cfg was created
            assert pydistutils.read_text() == DISTUTILS_CFG_NO_PREFIX
        else:
            # ~/.pydistutils.cfg was not modified
            assert pydistutils.read_text() == pydistutils_contents

    assert os.environ.get(PIP_REQUIRE_VIRTUALENV) == before_env_var

    # If a temporary ~/.pydistutils.cfg was created, it was deleted. If
    # ~/.pydistutils.cfg already existed, it still exists.
    assert pydistutils.exists() == bool(pydistutils_path)
