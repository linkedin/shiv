import os
import stat
import sys
import tempfile
import zipfile

from pathlib import Path
from zipapp import ZipAppError

import pytest

from shiv.builder import create_archive, rglob_follow_symlinks, write_file_prefix

UGOX = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH


def tmp_write_prefix(interpreter):
    with tempfile.TemporaryFile() as fd:
        write_file_prefix(fd, interpreter)
        fd.seek(0)
        written = fd.read()

    return written


class TestBuilder:
    @pytest.mark.parametrize(
        "interpreter,expected",
        [
            ("/usr/bin/python", b"#!/usr/bin/python\n"),
            ("/usr/bin/env python", b"#!/usr/bin/env python\n"),
            ("/some/other/path/python -sE", b"#!/some/other/path/python -sE\n"),
        ],
    )
    def test_file_prefix(self, interpreter, expected):
        assert tmp_write_prefix(interpreter) == expected

    def test_binprm_error(self):
        with pytest.raises(SystemExit):
            tmp_write_prefix(f"/{'c' * 200}/python")

    def test_rglob_follow_symlinks(self, tmp_path):
        real_dir = tmp_path / 'real_dir'
        real_dir.mkdir()
        real_file = real_dir / 'real_file'
        real_file.touch()
        sym_dir = tmp_path / 'sym_dir'
        sym_dir.symlink_to(real_dir)
        sym_file = sym_dir / real_file.name
        assert sorted(rglob_follow_symlinks(tmp_path, '*'), key=str) == [real_dir, real_file, sym_dir, sym_file]

    def test_create_archive(self, sp, env):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir, "test.zip")

            # create an archive
            create_archive(sp, target, sys.executable, "code:interact", env)

            # create one again (to ensure we overwrite)
            create_archive(sp, target, sys.executable, "code:interact", env)

            assert zipfile.is_zipfile(str(target))

            with pytest.raises(ZipAppError):
                create_archive(sp, target, sys.executable, "alsjdbas,,,", env)

    @pytest.mark.skipif(os.name == "nt", reason="windows has no concept of execute permissions")
    def test_archive_permissions(self, sp, env):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir, "test.zip")
            create_archive(sp, target, sys.executable, "code:interact", env)

            assert target.stat().st_mode & UGOX == UGOX
