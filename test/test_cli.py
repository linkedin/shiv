import subprocess
import sys
import tempfile

from pathlib import Path

import pytest

from click.testing import CliRunner

from shiv.cli import main, validate_interpreter
from shiv.constants import DISALLOWED_PIP_ARGS, NO_PIP_ARGS, NO_OUTFILE, BLACKLISTED_ARGS


def strip_header(output):
    return '\n'.join(output.splitlines()[1:])


class TestCLI:
    @pytest.fixture
    def runner(self):
        return lambda args: CliRunner().invoke(main, args)

    def test_no_args(self, runner):
        result = runner([])
        assert result.exit_code == 1
        assert strip_header(result.output) == NO_PIP_ARGS

    def test_no_outfile(self, runner):
        result = runner(['-e', 'test', 'flask'])
        assert result.exit_code == 1
        assert strip_header(result.output) == NO_OUTFILE

    @pytest.mark.parametrize("arg", [arg for tup in BLACKLISTED_ARGS.keys() for arg in tup])
    def test_blacklisted_args(self, runner, arg):
        result = runner(['-o', 'tmp', arg])

        # get the 'reason' message:
        for tup in BLACKLISTED_ARGS:
            if arg in tup:
                reason = BLACKLISTED_ARGS[tup]

        assert result.exit_code == 1

        # assert we got the correct reason
        assert strip_header(result.output) == DISALLOWED_PIP_ARGS.format(arg=arg, reason=reason)

    def test_hello_world(self, tmpdir, runner, package_location):
        with tempfile.TemporaryDirectory(dir=tmpdir) as tmpdir:
            output_file = Path(tmpdir, 'test.pyz')

            result = runner(['-e', 'hello:main', '-o', output_file.as_posix(), package_location.as_posix()])

            # check that the command successfully completed
            assert result.exit_code == 0

            # ensure the created file actually exists
            assert output_file.exists()

            # now run the produced zipapp
            with subprocess.Popen([output_file], stdout=subprocess.PIPE) as proc:
                assert proc.stdout.read().decode() == 'hello world\n'

    def test_interpreter(self):
        assert validate_interpreter(None) == validate_interpreter() == Path(sys.executable)

        with pytest.raises(SystemExit):
            validate_interpreter(Path('/usr/local/bogus_python'))

    @pytest.mark.skipif(len(sys.executable) > 128, reason='only run this test is the shebang is not too long')
    def test_real_interpreter(self):
        assert validate_interpreter(Path(sys.executable)) == Path(sys.executable)
