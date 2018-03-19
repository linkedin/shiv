import tempfile
import stat
import sys
import zipfile

from pathlib import Path
from zipapp import ZipAppError

import pytest

from shiv.cli import validate_interpreter
from shiv.builder import write_file_prefix, create_archive


UGOX = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH


class TestBuilder:
    def test_file_prefix(self):
        with tempfile.TemporaryFile() as fd:
            python = validate_interpreter(Path(sys.executable))
            write_file_prefix(fd, python)
            fd.seek(0)
            written = fd.read()

        assert written == b'#!' + python.as_posix().encode(sys.getdefaultencoding()) + b'\n'

    def test_create_archive(self, sp):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir, 'test.zip')
            create_archive(sp, target, validate_interpreter(None), 'code:interact')

            assert zipfile.is_zipfile(str(target))

            with pytest.raises(ZipAppError):
                create_archive(sp, target, validate_interpreter(None), 'alsjdbas,,,')

    def test_archive_permissions(self, sp):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir, 'test.zip')
            create_archive(sp, target, validate_interpreter(None), 'code:interact')

            assert target.stat().st_mode & UGOX == UGOX
