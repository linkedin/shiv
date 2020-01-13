import contextlib
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile

from pathlib import Path

import pytest

from click.testing import CliRunner
from shiv.cli import _interpreter_path, console_script_exists, find_entry_point, main
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
        def invoke(args, env=None):
            return CliRunner().invoke(main, args, env=env)

        return invoke

    @pytest.fixture
    def info_runner(self):
        """Returns a click test runner (for shiv-info)."""

        return lambda args: CliRunner().invoke(info_main, args)

    def test_find_entry_point(self, tmpdir, package_location):
        """Test that we can find console_script metadata."""
        install(["-t", str(tmpdir), str(package_location)])
        assert find_entry_point([Path(tmpdir)], "hello") == "hello:main"

    def test_find_entry_point_two_points(self, tmpdir, package_location):
        """Test that we can find console_script metadata."""
        install(["-t", str(tmpdir), str(package_location)])
        assert find_entry_point([Path(tmpdir)], "hello") == "hello:main"

    def test_console_script_exists(self, tmpdir, package_location):
        """Test that we can check console_script presence."""
        install_dir = os.path.join(tmpdir, 'install')
        install(["-t", str(install_dir), str(package_location)])
        empty_dir = os.path.join(tmpdir, 'empty')
        os.makedirs(empty_dir)

        assert console_script_exists([Path(empty_dir), Path(install_dir)], "hello")

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

    def test_multiple_site_packages(self, shiv_root, runner):
        output_file = Path(shiv_root, "test_multiple_sp.pyz")
        package_dir = Path(shiv_root, "package")
        main_script = Path(package_dir, "hello.py")

        env_code = "\n".join(["import os", "def hello():", "    print('hello!')"])

        package_dir.mkdir()
        main_script.write_text(env_code)

        other_package_dir = Path(shiv_root, "dependent_package")
        main_script = Path(package_dir, "hello_client.py")

        env_client_code = "\n".join(["import os", "from hello import hello", "def main():", "    hello()"])

        other_package_dir.mkdir()
        main_script.write_text(env_client_code)

        result = runner(["-e", "hello_client:main", "-o", str(output_file), "--site-packages", str(package_dir),
                         "--site-packages", str(other_package_dir)])

        # check that the command successfully completed
        assert result.exit_code == 0

        # ensure the created file actually exists
        assert output_file.exists()

        # now run the produced zipapp and confirm that output is ok
        proc = subprocess.run([str(output_file)], stdout=subprocess.PIPE, shell=True, env=os.environ)
        assert 'hello!' in proc.stdout.decode()

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

    def test_results_are_binary_identical_with_env_and_build_id(self, shiv_root, runner, package_location):
        first_output_file = Path(shiv_root, "test_one.pyz")
        second_output_file = Path(shiv_root, "test_two.pyz")

        result_one = runner(["-e", "hello:main", "-o", str(first_output_file), "--reproducible",
                             str(package_location)],
                            env={'SOURCE_DATE_EPOCH': '1234567890'})  # 2009-02-13 23:31:30 UTC

        result_two = runner(["-e", "hello:main", "-o", str(second_output_file), "--reproducible",
                             str(package_location)],
                            env={'SOURCE_DATE_EPOCH': '1234567890'})  # 2009-02-13 23:31:30 UTC

        # check that both commands successfully completed
        assert result_one.exit_code == 0
        assert result_two.exit_code == 0

        # check that both executables are binary identical
        with first_output_file.open('rb') as f:
            first_hash = hashlib.md5(f.read()).hexdigest()
        with second_output_file.open('rb') as f:
            second_hash = hashlib.md5(f.read()).hexdigest()

        assert first_hash == second_hash

        # finally, check that one of the result works
        proc = subprocess.run(
            [str(first_output_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            env=os.environ,
        )

        assert proc.returncode == 0
        assert 'hello' in proc.stdout.decode()
