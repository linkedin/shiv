import os
import sys

from contextlib import contextmanager
from pathlib import Path
from site import addsitedir
from code import interact
from uuid import uuid4
from zipfile import ZipFile

import pytest

from unittest import mock

from shiv.bootstrap import import_string, current_zipfile, cache_path
from shiv.bootstrap.environment import Environment


@contextmanager
def env_var(key, value):
    os.environ[key] = value
    yield
    del os.environ[key]


class TestBootstrap:
    def test_various_imports(self):
        assert import_string('site.addsitedir') == addsitedir
        assert import_string('site:addsitedir') == addsitedir
        assert import_string('code.interact') == interact
        assert import_string('code:interact') == interact

        # test things not already imported
        func = import_string('os.path:join')
        from os.path import join
        assert func == join

        # test something already imported
        import shiv
        assert import_string('shiv') == shiv == sys.modules['shiv']

        # test bogus imports raise properly
        with pytest.raises(ImportError):
            import_string('this is bogus!')

    def test_is_zipfile(self, zip_location):
        with mock.patch.object(sys, 'argv', [zip_location]):
            assert isinstance(current_zipfile(), ZipFile)

    # When the tests are run via tox, sys.argv[0] is the full path to 'pytest.EXE',
    # i.e. a native launcher created by pip to from console_scripts entry points.
    # These are indeed a form of zip files, thus the following assertion could fail.
    @pytest.mark.skipif(os.name == 'nt', reason="this may give false positive on win")
    def test_argv0_is_not_zipfile(self):
        assert not current_zipfile()

    def test_cache_path(self):
        mock_zip = mock.MagicMock(spec=ZipFile)
        mock_zip.filename = "test"
        uuid = str(uuid4())

        assert cache_path(mock_zip, Path.cwd(), uuid) == Path.cwd() / f"test_{uuid}"


class TestEnvironment:
    def test_overrides(self):
        env = Environment()

        assert env.entry_point is None
        with env_var('SHIV_ENTRY_POINT', 'test'):
            assert env.entry_point == 'test'

        assert env.interpreter is None
        with env_var('SHIV_INTERPRETER', '1'):
            assert env.interpreter is not None

        assert env.root is None
        with env_var('SHIV_ROOT', 'tmp'):
            assert env.root == Path('tmp')

        assert env.force_extract is False
        with env_var('SHIV_FORCE_EXTRACT', '1'):
            assert env.force_extract is True

    def test_serialize(self):
        env = Environment()
        env_as_json = env.to_json()
        env_from_json = Environment.from_json(env_as_json)
        assert env.__dict__ == env_from_json.__dict__
