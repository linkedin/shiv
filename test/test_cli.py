import os
import subprocess
import tempfile

from pathlib import Path

import pytest

from click.testing import CliRunner

from shiv.cli import main, _interpreter_path
from shiv.constants import DISALLOWED_PIP_ARGS, NO_PIP_ARGS_OR_SITE_PACKAGES, NO_OUTFILE, BLACKLISTED_ARGS


def strip_header(output):
    return '\n'.join(output.splitlines()[1:])


class TestCLI:
    @pytest.fixture
    def runner(self):
        return lambda args: CliRunner().invoke(main, args)

    def test_no_args(self, runner):
        result = runner([])
        assert result.exit_code == 1
        assert strip_header(result.output) == NO_PIP_ARGS_OR_SITE_PACKAGES

    def test_no_outfile(self, runner):
        result = runner(['-e', 'test', 'flask'])
        assert result.exit_code == 1
        assert strip_header(result.output) == NO_OUTFILE

    def test_find_interpreter(self):
        interpreter = _interpreter_path()
        assert Path(interpreter).exists()
        assert Path(interpreter).is_file()

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

    @pytest.mark.parametrize('compile_option', ["--compile-pyc", "--no-compile-pyc"])
    def test_hello_world(self, tmpdir, runner, package_location, compile_option, monkeypatch):

        with tempfile.TemporaryDirectory(dir=tmpdir) as tmpdir:
            output_file = Path(tmpdir, 'test.pyz')

            result = runner(['-e', 'hello:main', '-o', str(output_file), str(package_location), compile_option])

            # check that the command successfully completed
            assert result.exit_code == 0

            # ensure the created file actually exists
            assert output_file.exists()

            # now run the produced zipapp
            with monkeypatch.context() as m:
                m.setenv('SHIV_ROOT', tmpdir)
                with subprocess.Popen([str(output_file)], stdout=subprocess.PIPE, shell=True) as proc:
                    assert proc.stdout.read().decode() == "hello world" + os.linesep

    @pytest.mark.parametrize('env_option', ["--extend-pythonpath", "--no-extend-pythonpath", "-E"])
    def test_extend_pythonpath(self, tmpdir, runner, monkeypatch, env_option):

        with tempfile.TemporaryDirectory(dir=tmpdir) as tmpdir:
            output_file = Path(tmpdir, 'test_pythonpath.pyz')
            package_dir = Path(tmpdir, 'package')
            shiv_root = Path(tmpdir, 'shiv')
            main_script = Path(package_dir, 'env.py')

            MAIN_PROG = '\n'.join([
                "import os",
                "def main():",
                "    print(os.environ.get('PYTHONPATH', ''))"
            ])

            package_dir.mkdir()
            shiv_root.mkdir()
            main_script.write_text(MAIN_PROG)

            result = runner([
                '-e', 'env:main',
                '-o', str(output_file),
                '--site-packages', str(package_dir),
                env_option
            ])

            # check that the command successfully completed
            assert result.exit_code == 0

            # ensure the created file actually exists
            assert output_file.exists()

            # now run the produced zipapp and confirm shiv_root is in PYTHONPATH
            with monkeypatch.context() as m:
                m.setenv('SHIV_ROOT', str(shiv_root))
                with subprocess.Popen([str(output_file)], stdout=subprocess.PIPE, shell=True) as proc:
                    pythonpath_has_root = (str(shiv_root) in proc.stdout.read().decode())
                    assert env_option.startswith('--no') != pythonpath_has_root
