import contextlib
import hashlib
import json
import os
import stat
import subprocess
import sys

from pathlib import Path

import pytest

from click.testing import CliRunner
from shiv.cli import console_script_exists, find_entry_point, main
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
    def shiv_root(self, monkeypatch, tmp_path):
        os.environ["SHIV_ROOT"] = str(tmp_path)
        yield tmp_path
        os.environ.pop("SHIV_ROOT")

    @pytest.fixture
    def runner(self):
        """Returns a click test runner."""

        def invoke(args, env=None):
            args.extend(["-p", "/usr/bin/env python3"])
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

    def test_console_script_exists(self, tmp_path, package_location):
        """Test that we can check console_script presence."""
        install_dir = tmp_path / "install"
        install(["-t", str(install_dir), str(package_location)])
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        assert console_script_exists([empty_dir, install_dir], "hello.exe" if os.name == "nt" else "hello")

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

    @pytest.mark.parametrize("arg", [arg for tup in DISALLOWED_ARGS.keys() for arg in tup])
    def test_disallowed_args(self, runner, arg):
        """This method tests that all the potential disallowed arguments match their error messages."""

        # run shiv with a disallowed argument
        result = runner(["-o", "tmp", arg])

        # get the 'reason' message:
        reason = next(iter([DISALLOWED_ARGS[disallowed] for disallowed in DISALLOWED_ARGS if arg in disallowed]))

        assert result.exit_code == 1

        # assert we got the correct reason
        assert DISALLOWED_PIP_ARGS.format(arg=arg, reason=reason) in result.output

    @pytest.mark.parametrize("compile_option", [["--compile-pyc"], ["--build-id", "42424242"], []])
    @pytest.mark.parametrize("force", ["yes", "no"])
    def test_hello_world(self, runner, info_runner, shiv_root, package_location, compile_option, force):
        output_file = shiv_root / "test.pyz"

        result = runner(["-e", "hello:main", "-o", str(output_file), str(package_location), *compile_option])

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
            if "--build-id" in compile_option:
                assert build_id == compile_option[1]
            assert (
                Path(shiv_root, f"{output_file.name}_{build_id}", "site-packages", "hello", "script.sh").stat().st_mode
                & UGOX
                == UGOX
            )

    @pytest.mark.parametrize("extend_path", [["--extend-pythonpath"], ["-E"], []])
    def test_extend_pythonpath(self, shiv_root, runner, extend_path):

        output_file = Path(shiv_root, "test_pythonpath.pyz")
        package_dir = Path(shiv_root, "package")
        main_script = Path(package_dir, "env.py")

        # noinspection PyPep8Naming
        MAIN_PROG = "\n".join(["import os", "def main():", "    print(os.environ.get('PYTHONPATH', ''))"])

        package_dir.mkdir()
        main_script.write_text(MAIN_PROG)

        result = runner(["-e", "env:main", "-o", str(output_file), "--site-packages", str(package_dir), *extend_path])

        # check that the command successfully completed
        assert result.exit_code == 0

        # ensure the created file actually exists
        assert output_file.exists()

        # now run the produced zipapp and confirm shiv_root is in PYTHONPATH
        proc = subprocess.run([str(output_file)], stdout=subprocess.PIPE, shell=True, env=os.environ)

        pythonpath_has_root = str(shiv_root) in proc.stdout.decode()
        if extend_path:
            assert pythonpath_has_root

    def test_multiple_site_packages(self, shiv_root, runner):
        output_file = shiv_root / "test_multiple_sp.pyz"
        package_dir = shiv_root / "package"
        main_script = package_dir / "hello.py"

        env_code = "\n".join(["import os", "def hello():", "    print('hello!')"])

        package_dir.mkdir()
        main_script.write_text(env_code)

        other_package_dir = shiv_root / "dependent_package"
        main_script = package_dir / "hello_client.py"

        env_client_code = "\n".join(["import os", "from hello import hello", "def main():", "    hello()"])

        other_package_dir.mkdir()
        main_script.write_text(env_client_code)

        result = runner(
            [
                "-e",
                "hello_client:main",
                "-o",
                str(output_file),
                "--site-packages",
                str(package_dir),
                "--site-packages",
                str(other_package_dir),
            ]
        )

        # check that the command successfully completed
        assert result.exit_code == 0

        # ensure the created file actually exists
        assert output_file.exists()

        # now run the produced zipapp and confirm that output is ok
        proc = subprocess.run([str(output_file)], stdout=subprocess.PIPE, shell=True, env=os.environ)
        assert "hello!" in proc.stdout.decode()

    def test_no_entrypoint(self, shiv_root, runner, package_location):

        output_file = shiv_root / "test.pyz"

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

    @pytest.mark.skipif(
        os.name == "nt", reason="windows creates .exe files for entry points, which are not reproducible :("
    )
    def test_results_are_binary_identical_with_env_and_build_id(self, shiv_root, runner, package_location):
        first_output_file = shiv_root / "test_one.pyz"
        second_output_file = shiv_root / "test_two.pyz"

        result_one = runner(
            ["-e", "hello:main", "-o", str(first_output_file), "--reproducible", "--no-modify", str(package_location)],
            env={"SOURCE_DATE_EPOCH": "1234567890"},
        )  # 2009-02-13 23:31:30 UTC

        result_two = runner(
            ["-e", "hello:main", "-o", str(second_output_file), "--reproducible", "--no-modify", str(package_location)],
            env={"SOURCE_DATE_EPOCH": "1234567890"},
        )  # 2009-02-13 23:31:30 UTC

        # check that both commands successfully completed
        assert result_one.exit_code == 0
        assert result_two.exit_code == 0

        # check that both executables are binary identical
        assert (
            hashlib.md5(first_output_file.read_bytes()).hexdigest()
            == hashlib.md5(second_output_file.read_bytes()).hexdigest()
        )

        # finally, check that one of the result works
        proc = subprocess.run(
            [str(first_output_file)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, env=os.environ,
        )

        assert proc.returncode == 0
        assert "hello" in proc.stdout.decode()

    @pytest.mark.skipif(
        os.name == "nt", reason="can't run a shell script on windows"
    )
    @pytest.mark.parametrize(
        "preamble, contents",
        [
            ("preamble.py", "#!/usr/bin/env python3\nprint('hello from preamble')"),
            ("preamble.sh", "#!/bin/sh\necho 'hello from preamble'"),
        ],
    )
    def test_preamble(self, preamble, contents, shiv_root, runner, package_location, tmp_path):
        """Test the --preamble argument."""

        output_file = shiv_root / "test.pyz"
        preamble = tmp_path / preamble
        preamble.write_text(contents)
        preamble.chmod(preamble.stat().st_mode | stat.S_IEXEC)

        result = runner(
            ["-e", "hello:main", "--preamble", str(preamble), "-o", str(output_file), str(package_location)]
        )

        # check that the command successfully completed
        assert result.exit_code == 0

        # ensure the created file actually exists
        assert output_file.exists()

        # now run the produced zipapp
        proc = subprocess.run(
            [str(output_file)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, env=os.environ,
        )

        assert proc.returncode == 0
        assert proc.stdout.decode().splitlines() == ["hello from preamble", "hello world"]

    def test_preamble_no_pip(self, shiv_root, runner, package_location, tmp_path):
        """Test that the preamble script is created even with no pip installed packages."""

        output_file = shiv_root / "test.pyz"
        target = tmp_path / "target"
        preamble = tmp_path / "preamble.py"
        preamble.write_text("#!/usr/bin/env python3\nprint('hello from preamble')")
        preamble.chmod(preamble.stat().st_mode | stat.S_IEXEC)

        # first, by installing our test package into a target
        install(["-t", str(target), str(package_location)])
        result = runner(
            ["-e", "hello:main", "--preamble", str(preamble), "-o", str(output_file), "--site-packages", target]
        )

        # check that the command successfully completed
        assert result.exit_code == 0

        # ensure the created file actually exists
        assert output_file.exists()

        # now run the produced zipapp
        proc = subprocess.run(
            [str(output_file)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, env=os.environ,
        )

        assert proc.returncode == 0
        assert proc.stdout.decode().splitlines() == ["hello from preamble", "hello world"]

    def test_alternate_root(self, runner, package_location, tmp_path):
        """Test that the --root argument properly sets the extraction root."""

        output_file = tmp_path / "test.pyz"
        shiv_root = tmp_path / "root"
        result = runner(
            ["-e", "hello:main", "--root", str(shiv_root), "-o", str(output_file), str(package_location)]
        )

        # check that the command successfully completed
        assert result.exit_code == 0

        # ensure the created file actually exists
        assert output_file.exists()

        # now run the produced zipapp
        proc = subprocess.run(
            [str(output_file)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, env=os.environ,
        )

        assert proc.returncode == 0
        assert "hello" in proc.stdout.decode()
        assert shiv_root.exists()

    def test_alternate_root_environment_variable(self, runner, package_location, tmp_path, env_var):
        """Test that the --root argument works with environment variables."""

        output_file = tmp_path / "test.pyz"
        shiv_root_var = "NEW_ROOT"
        shiv_root_path = tmp_path / 'new_root'
        result = runner(
            ["-e", "hello:main", "--root", "$" + shiv_root_var, "-o", str(output_file), str(package_location)]
        )

        with env_var(shiv_root_var, str(shiv_root_path)):

            # check that the command successfully completed
            assert result.exit_code == 0

            # ensure the created file actually exists
            assert output_file.exists()

            # now run the produced zipapp
            proc = subprocess.run(
                [str(output_file)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, env=os.environ,
            )

        assert proc.returncode == 0
        assert "hello" in proc.stdout.decode()
        assert shiv_root_path.exists()
