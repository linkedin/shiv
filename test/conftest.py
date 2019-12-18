import os

from pathlib import Path

import pytest

from shiv.bootstrap.environment import Environment


@pytest.fixture
def zip_location():
    return Path(__file__).absolute().parent / "test.zip"


@pytest.fixture(params=[True, False], ids=[".", "absolute-path"])
def package_location(request):
    package_location = Path(__file__).absolute().parent / "package"

    if request.param is True:
        # test building from the current directory
        cwd = os.getcwd()
        os.chdir(package_location)
        yield Path(".")
        os.chdir(cwd)
    else:
        # test building an absolute path
        yield package_location


@pytest.fixture
def sp():
    return [Path(__file__).absolute().parent / 'sp' / 'site-packages']


@pytest.fixture
def env():
    return Environment(
        built_at=str("2019-01-01 12:12:12"),
        build_id=str("test_id"),
        entry_point="test_entry_point",
        script="test_console_script",
        compile_pyc=False,
        extend_pythonpath=False,
        shiv_version="0.0.1",
    )
