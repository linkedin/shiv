import os

from pathlib import Path

import pytest


@pytest.fixture
def zip_location():
    return Path(__file__).absolute().parent / 'test.zip'


@pytest.fixture(params=[True, False], ids=['.', 'absolute-path'])
def package_location(request):
    package_location = Path(__file__).absolute().parent / 'package'

    if request.param is True:
        # test building from the current directory
        cwd = os.getcwd()
        os.chdir(package_location)
        yield Path('.')
        os.chdir(cwd)
    else:
        # test building an absolute path
        yield package_location


@pytest.fixture
def sp():
    return Path(__file__).absolute().parent / 'sp' / 'site-packages'
