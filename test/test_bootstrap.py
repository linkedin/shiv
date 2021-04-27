import os
import sys

from code import interact
from datetime import datetime
from pathlib import Path
from site import addsitedir
from unittest import mock
from uuid import uuid4
from zipfile import ZipFile

import pytest

from shiv.bootstrap import (
    cache_path,
    current_zipfile,
    ensure_no_modify,
    extend_python_path,
    extract_site_packages,
    get_first_sitedir_index,
    import_string,
)
from shiv.bootstrap.environment import Environment
from shiv.bootstrap.filelock import FileLock
from shiv.pip import install


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
            with current_zipfile() as zipfile:
                assert isinstance(zipfile, ZipFile)

    # When the tests are run via tox, sys.argv[0] is the full path to 'pytest.EXE',
    # i.e. a native launcher created by pip to from console_scripts entry points.
    # These are indeed a form of zip files, thus the following assertion could fail.
    @pytest.mark.skipif(os.name == "nt", reason="this may give false positive on win")
    def test_argv0_is_not_zipfile(self):
        with current_zipfile() as zipfile:
            assert not zipfile

    def test_cache_path(self, env_var):
        mock_zip = mock.MagicMock(spec=ZipFile)
        mock_zip.filename = "test"
        uuid = str(uuid4())

        assert cache_path(mock_zip, 'foo', uuid) == Path("foo", f"test_{uuid}")

        with env_var("FOO", "foo"):
            assert cache_path(mock_zip, '$FOO', uuid) == Path("foo", f"test_{uuid}")

    def test_first_sitedir_index(self):
        with mock.patch.object(sys, "path", ["site-packages", "dir", "dir", "dir"]):
            assert get_first_sitedir_index() == 0

        with mock.patch.object(sys, "path", []):
            assert get_first_sitedir_index() is None

    @pytest.mark.parametrize("nested", (False, True))
    @pytest.mark.parametrize("compile_pyc", (False, True))
    @pytest.mark.parametrize("force", (False, True))
    def test_extract_site_packages(self, tmp_path, zip_location, nested, compile_pyc, force):

        zipfile = ZipFile(str(zip_location))
        target = tmp_path / "test"

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

        env = {}

        extend_python_path(env, additional_paths)
        assert env["PYTHONPATH"] == os.pathsep.join(additional_paths)

    def test_extend_path_existing_pythonpath(self):
        """When PYTHONPATH exists, extending it preserves the existing values."""
        env = {"PYTHONPATH": "hello"}

        extend_python_path(env, ["test", ".pth"])
        assert env["PYTHONPATH"] == os.pathsep.join(["hello", "test", ".pth"])


class TestEnvironment:
    def test_overrides(self, env_var):
        now = str(datetime.now())
        version = "0.0.1"
        env = Environment(now, version)

        assert env.built_at == now
        assert env.shiv_version == version

        assert env.entry_point is None
        with env_var("SHIV_ENTRY_POINT", "test"):
            assert env.entry_point == "test"

        assert env.script is None
        with env_var("SHIV_CONSOLE_SCRIPT", "test"):
            assert env.script == "test"

        assert env.interpreter is None
        with env_var("SHIV_INTERPRETER", "1"):
            assert env.interpreter is not None

        assert env.root is None
        with env_var("SHIV_ROOT", "tmp"):
            assert env.root == "tmp"

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

    def test_lock(self, tmp_path):
        with FileLock(str(tmp_path / "lockfile")) as f:
            assert f.is_locked

        assert not f.is_locked

    @pytest.mark.skipif(
        os.name == "nt", reason="windows creates .exe files for entry points, which are not reproducible :("
    )
    def test_ensure_no_modify(self, tmp_path, package_location):

        # Populate a site-packages dir
        site_packages = tmp_path / "site-packages"
        install(["-t", str(site_packages), str(package_location)])

        for test_hash in [{"abc": "123"}, {"hello/__init__.py": "123"}]:
            with pytest.raises(RuntimeError):
                ensure_no_modify(site_packages, test_hash)

        # the hash of the only source file the test package provides
        hashes = {"hello/__init__.py": "1e8d5b8a6839487a4211229f69b76a5f901515dcad7f111a4bdd5b30d9e96020"}

        ensure_no_modify(site_packages, hashes)
