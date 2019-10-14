import contextlib
import json
import os
import stat
import subprocess
import sys
import tempfile

from pathlib import Path

import pytest

from click.testing import CliRunner
from shiv.cli import _interpreter_path, find_entry_point, main
from shiv.constants import DISALLOWED_ARGS, DISALLOWED_PIP_ARGS, NO_OUTFILE, NO_PIP_ARGS_OR_SITE_PACKAGES
from shiv.info import main as info_main
from shiv.pip import install

UGOX = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH


@contextlib.contextmanager
def mocked_sys_prefix():
    attribute_to_mock = "real_prefix" if hasattr(sys, "real_prefix") else "base_prefix"
    original = getattr(sys, attribute_to_mock)
    setattr(sys, attribute_to_mock, "/fake/dir")
    yield
    setattr(sys, attribute_to_mock, original)


class TestCLI:
    @pytest.fixture
    def shiv_root(self, monkeypatch, tmpdir):

        with tempfile.TemporaryDirectory(dir=tmpdir) as tmpdir:
            os.environ["SHIV_ROOT"] = tmpdir
            yield tmpdir

        os.environ.pop("SHIV_ROOT")

    @pytest.fixture
    def runner(self):
        """Returns a click test runner."""

        return lambda args: CliRunner().invoke(main, args)

    @pytest.fixture
    def info_runner(self):
        """Returns a click test runner (for shiv-info)."""

        return lambda args: CliRunner().invoke(info_main, args)

    def test_find_entry_point(self, tmpdir, package_location):
        """Test that we can find console_script metadata."""
        install(["-t", str(tmpdir), str(package_location)])
        assert find_entry_point(Path(tmpdir), "hello") == "hello:main"

    def test_no_args(self, runner):
        """This should fail with a warning about supplying pip arguments"""

        result = runner([])

        assert result.exit_code == 1
        assert NO_PIP_ARGS_OR_SITE_PACKAGES in result.output

    def test_no_outfile(self, runner):
        """This should fail with a warning about not providing an outfile"""

        result = runner(["-e", "test", "flask"])

        assert result.exit_code == 1
        assert NO_OUTFILE in result.output

    def test_find_interpreter(self):

        interpreter = _interpreter_path()

        assert Path(interpreter).exists()
        assert Path(interpreter).is_file()

    def test_find_interpreter_false(self):

        with mocked_sys_prefix():
            interpreter = _interpreter_path()

        # should fall back on the current sys.executable
        assert interpreter == sys.executable

    @pytest.mark.parametrize("arg", [arg for tup in DISALLOWED_ARGS.keys() for arg in tup])
    def test_disallowed_args(self, runner, arg):
        """This method tests that all the potential disallowed arguments match their error messages."""

        # run shiv with a disallowed argument
        result = runner(["-o", "tmp", arg])

        # get the 'reason' message:
        for disallowed in DISALLOWED_ARGS:
            if arg in disallowed:
                reason = DISALLOWED_ARGS[disallowed]

        assert result.exit_code == 1

        # assert we got the correct reason
        assert DISALLOWED_PIP_ARGS.format(arg=arg, reason=reason) in result.output

    @pytest.mark.parametrize("compile_option", ["--compile-pyc", "--no-compile-pyc"])
    @pytest.mark.parametrize("force", ["yes", "no"])
    def test_hello_world(self, runner, info_runner, shiv_root, package_location, compile_option, force):
        output_file = Path(shiv_root, "test.pyz")

        result = runner(["-e", "hello:main", "-o", str(output_file), str(package_location), compile_option])

        # check that the command successfully completed
        assert result.exit_code == 0

        # ensure the created file actually exists
        assert output_file.exists()

        # build env
        env = {**os.environ, "SHIV_FORCE_EXTRACT": force}

        # now run the produced zipapp
        proc = subprocess.run([str(output_file)], stdout=subprocess.PIPE, shell=True, env=env)

        assert proc.stdout.decode() == "hello world" + os.linesep

        # now run shiv-info on the produced zipapp
        result = info_runner([str(output_file)])

        # check the rc and output
        assert result.exit_code == 0
        assert f"pyz file: {str(output_file)}" in result.output

        # ensure that executable permissions were retained (skip test on windows)
        if os.name != "nt":
            build_id = json.loads(info_runner([str(output_file), "--json"]).output)["build_id"]
            assert (
                Path(shiv_root, f"{output_file.stem}_{build_id}", "site-packages", "hello", "script.sh").stat().st_mode
                & UGOX
                == UGOX
            )

    @pytest.mark.parametrize("extend_path", ["--extend-pythonpath", "--no-extend-pythonpath", "-E"])
    def test_extend_pythonpath(self, shiv_root, runner, extend_path):

        output_file = Path(shiv_root, "test_pythonpath.pyz")
        package_dir = Path(shiv_root, "package")
        main_script = Path(package_dir, "env.py")

        MAIN_PROG = "\n".join(["import os", "def main():", "    print(os.environ.get('PYTHONPATH', ''))"])

        package_dir.mkdir()
        main_script.write_text(MAIN_PROG)

        result = runner(["-e", "env:main", "-o", str(output_file), "--site-packages", str(package_dir), extend_path])

        # check that the command successfully completed
        assert result.exit_code == 0

        # ensure the created file actually exists
        assert output_file.exists()

        # now run the produced zipapp and confirm shiv_root is in PYTHONPATH
        proc = subprocess.run([str(output_file)], stdout=subprocess.PIPE, shell=True, env=os.environ)

        pythonpath_has_root = str(shiv_root) in proc.stdout.decode()
        assert extend_path.startswith("--no") != pythonpath_has_root

    def test_no_entrypoint(self, shiv_root, runner, package_location, monkeypatch):

        output_file = Path(shiv_root, "test.pyz")

        result = runner(["-o", str(output_file), str(package_location)])

        # check that the command successfully completed
        assert result.exit_code == 0

        # ensure the created file actually exists
        assert output_file.exists()

        # now run the produced zipapp
        proc = subprocess.run(
            [str(output_file)],
            input=b"import hello;print(hello)",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            env=os.environ,
        )

        assert proc.returncode == 0
        assert "hello" in proc.stdout.decode()
