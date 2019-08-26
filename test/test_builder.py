import tempfile
import stat
import os
import sys
import zipfile

from pathlib import Path
from zipapp import ZipAppError

import pytest

from shiv.builder import write_file_prefix, create_archive


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

    def test_create_archive(self, sp):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir, "test.zip")

            # create an archive
            create_archive(sp, target, sys.executable, "code:interact")

            # create one again (to ensure we overwrite)
            create_archive(sp, target, sys.executable, "code:interact")

            assert zipfile.is_zipfile(str(target))

            with pytest.raises(ZipAppError):
                create_archive(sp, target, sys.executable, "alsjdbas,,,")

    def test_create_archive_filter(self):
        with tempfile.TemporaryDirectory() as tmpdir, tempfile.TemporaryDirectory() as sourceDir:
            filtered_target = Path(tmpdir, "test.zip")
            unfiltered_target = Path(tmpdir, "test2.zip")
            open(Path(sourceDir, "test.py"), "a").close()

            create_archive(Path(sourceDir), filtered_target, sys.executable, "code:interact", lambda _: False)
            create_archive(Path(sourceDir), unfiltered_target, sys.executable, "code:interact")

            assert zipfile.is_zipfile(str(filtered_target))
            assert len(zipfile.ZipFile(str(filtered_target)).filelist) == 1 # At least there is __main__.py
            assert zipfile.is_zipfile(str(unfiltered_target))
            assert len(zipfile.ZipFile(str(unfiltered_target)).filelist) == 2 # __main__.py + test.py

    def test_create_archive_dot_shivignore(self):
        try:
            cwd = os.getcwd()
            with tempfile.TemporaryDirectory() as tmpdir, tempfile.TemporaryDirectory() as sourceDir:
                filtered_target = Path(tmpdir, "test.zip")
                unfiltered_target = Path(tmpdir, "test2.zip")
                open(Path(sourceDir, "test.py"), "a").close()
                os.chdir(sourceDir)

                create_archive(Path(sourceDir), unfiltered_target, sys.executable, "code:interact")

                # Add the .shivignore
                with open(Path(sourceDir, ".shivignore"), "a") as f:
                    f.write("*")
                create_archive(Path(sourceDir), filtered_target, sys.executable, "code:interact")

                # Filtered zipfile
                assert zipfile.is_zipfile(str(filtered_target))
                assert len(zipfile.ZipFile(str(filtered_target)).filelist) == 1
                # Unfiltered zipfile
                assert zipfile.is_zipfile(str(unfiltered_target))
                assert len(zipfile.ZipFile(str(unfiltered_target)).filelist) == 2
        finally:
            os.chdir(cwd)


    @pytest.mark.skipif(
        os.name == "nt", reason="windows has no concept of execute permissions"
    )
    def test_archive_permissions(self, sp):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir, "test.zip")
            create_archive(sp, target, sys.executable, "code:interact")

            assert target.stat().st_mode & UGOX == UGOX
