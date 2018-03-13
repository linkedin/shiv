from pathlib import Path

import pytest


@pytest.fixture
def package_location():
    return str(
        Path(Path(__file__).absolute().parent, 'package'),
    )


@pytest.fixture
def sp():
    return str(
        Path(Path(__file__).absolute().parent, 'sp', 'site-packages'),
    )
