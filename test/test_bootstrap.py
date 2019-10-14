import os
import sys

from code import interact
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from site import addsitedir
from unittest import mock
from uuid import uuid4
from zipfile import ZipFile

import pytest

from shiv.bootstrap import (
    _extend_python_path,
    _first_sitedir_index,
    cache_path,
    current_zipfile,
    extract_site_packages,
    import_string,
)
from shiv.bootstrap.environment import Environment
from shiv.bootstrap.filelock import FileLock


@contextmanager
def env_var(key, value):
    os.environ[key] = value
    yield
    del os.environ[key]


class TestBootstrap:
    def test_import_string(self):
        assert import_string("site.addsitedir") == addsitedir
        assert import_string("site:addsitedir") == addsitedir
        assert import_string("code.interact") == interact
        assert import_string("code:interact") == interact

        # test things not already imported
        func = import_string("os.path:join")
        from os.path import join

        assert func == join

        # test something already imported
        import shiv

        assert import_string("shiv") == shiv == sys.modules["shiv"]

        # test bogus imports raise properly
        with pytest.raises(ImportError):
            import_string("this is bogus!")

    def test_is_zipfile(self, zip_location):
        with mock.patch.object(sys, "argv", [zip_location]):
            assert isinstance(current_zipfile(), ZipFile)

    # When the tests are run via tox, sys.argv[0] is the full path to 'pytest.EXE',
    # i.e. a native launcher created by pip to from console_scripts entry points.
    # These are indeed a form of zip files, thus the following assertion could fail.
    @pytest.mark.skipif(os.name == "nt", reason="this may give false positive on win")
    def test_argv0_is_not_zipfile(self):
        assert not current_zipfile()

    def test_cache_path(self):
        mock_zip = mock.MagicMock(spec=ZipFile)
        mock_zip.filename = "test"
        uuid = str(uuid4())

        assert cache_path(mock_zip, Path.cwd(), uuid) == Path.cwd() / f"test_{uuid}"

    def test_first_sitedir_index(self):
        with mock.patch.object(sys, "path", ["site-packages", "dir", "dir", "dir"]):
            assert _first_sitedir_index() == 0

        with mock.patch.object(sys, "path", []):
            assert _first_sitedir_index() is None

    @pytest.mark.parametrize("nested", (False, True))
    @pytest.mark.parametrize("compile_pyc", (False, True))
    @pytest.mark.parametrize("force", (False, True))
    def test_extract_site_packages(self, tmpdir, zip_location, nested, compile_pyc, force):

        zipfile = ZipFile(str(zip_location))
        target = Path(tmpdir, "test")

        if nested:
            # we want to test for not-yet-created shiv root dirs
            target = target / "nested" / "root"

        if force:
            # we want to make sure we overwrite if the target exists when using force
            target.mkdir(parents=True, exist_ok=True)

        # Do the extraction (of our empty zip file)
        extract_site_packages(zipfile, target, compile_pyc, force=force)

        site_packages = target / "site-packages"
        assert site_packages.exists()
        assert site_packages.is_dir()
        assert Path(site_packages, "test").exists()
        assert Path(site_packages, "test").is_file()

    @pytest.mark.parametrize("additional_paths", (["test"], ["test", ".pth"]))
    def test_extend_path(self, additional_paths):

        env = os.environ.copy()

        _extend_python_path(env, additional_paths)
        assert env["PYTHONPATH"] == os.pathsep.join(additional_paths)


class TestEnvironment:
    def test_overrides(self):
        now = str(datetime.now())
        version = "0.0.1"
        env = Environment(now, version)

        assert env.built_at == now
        assert env.shiv_version == version

        assert env.entry_point is None
        with env_var("SHIV_ENTRY_POINT", "test"):
            assert env.entry_point == "test"

        assert env.interpreter is None
        with env_var("SHIV_INTERPRETER", "1"):
            assert env.interpreter is not None

        assert env.root is None
        with env_var("SHIV_ROOT", "tmp"):
            assert env.root == Path("tmp")

        assert env.force_extract is False
        with env_var("SHIV_FORCE_EXTRACT", "1"):
            assert env.force_extract is True

        assert env.compile_pyc is True
        with env_var("SHIV_COMPILE_PYC", "False"):
            assert env.compile_pyc is False

        assert env.extend_pythonpath is False
        with env_var("SHIV_EXTEND_PYTHONPATH", "1"):
            assert env.compile_pyc is True

        assert env.compile_workers == 0
        with env_var("SHIV_COMPILE_WORKERS", "1"):
            assert env.compile_workers == 1

        # ensure that non-digits are ignored
        with env_var("SHIV_COMPILE_WORKERS", "one bazillion"):
            assert env.compile_workers == 0

    def test_roundtrip(self):
        now = str(datetime.now())
        version = "0.0.1"
        env = Environment(now, version)
        env_as_json = env.to_json()
        env_from_json = Environment.from_json(env_as_json)
        assert env.__dict__ == env_from_json.__dict__

    def test_lock(self):
        with FileLock("lockfile") as f:
            assert f.is_locked

        assert not f.is_locked
