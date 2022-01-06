import compileall
import hashlib
import os
import runpy
import shutil
import site
import subprocess
import sys
import zipfile

from contextlib import contextmanager, suppress
from functools import partial
from importlib import import_module
from pathlib import Path

from .environment import Environment
from .filelock import FileLock
from .interpreter import execute_interpreter


def run(module):  # pragma: no cover
    """Run a module in a scrubbed environment.

    If a single pyz has multiple callers, we want to remove these vars as we no longer need them
    and they can cause subprocesses to fail with a ModuleNotFoundError.

    :param Callable module: The entry point to invoke the pyz with.
    """
    with suppress(KeyError):
        del os.environ[Environment.MODULE]

    with suppress(KeyError):
        del os.environ[Environment.ENTRY_POINT]

    with suppress(KeyError):
        del os.environ[Environment.CONSOLE_SCRIPT]

    sys.exit(module())


@contextmanager
def current_zipfile():
    """A function to vend the current zipfile, if any"""
    if zipfile.is_zipfile(sys.argv[0]):
        with zipfile.ZipFile(sys.argv[0]) as fd:
            yield fd
    else:
        yield None


def import_string(import_name):
    """Returns a callable for a given setuptools style import string

    :param str import_name: A console_scripts style import string
    """
    import_name = str(import_name).replace(":", ".")

    try:
        import_module(import_name)

    except ImportError:
        if "." not in import_name:
            # this is a case like "import name", where continuing to the
            # next style of import would not improve the situation, so
            # we raise here.
            raise

    else:
        return sys.modules[import_name]

    # this is a case where the previous attempt may have failed due to
    # not being importable. ("not a package", etc)
    module_name, obj_name = import_name.rsplit(".", 1)

    try:
        module = __import__(module_name, None, None, [obj_name])

    except ImportError:
        # Recurse to support importing modules not yet set up by the parent module
        # (or package for that matter)
        module = import_string(module_name)

    try:
        return getattr(module, obj_name)

    except AttributeError as e:
        raise ImportError(e)


def cache_path(archive, root_dir, build_id):
    """Returns a ~/.shiv cache directory for unzipping site-packages during bootstrap.

    :param ZipFile archive: The zipfile object we are bootstrapping from.
    :param str root_dir: Optional, either a path or environment variable pointing to a SHIV_ROOT.
    :param str build_id: The build id generated at zip creation.
    """

    if root_dir:

        if root_dir.startswith("$"):
            root_dir = os.environ.get(root_dir[1:], root_dir[1:])

        root_dir = Path(root_dir).expanduser()

    root = root_dir or Path("~/.shiv").expanduser()
    name = Path(archive.filename).resolve().name
    return root / f"{name}_{build_id}"


def extract_site_packages(archive, target_path, compile_pyc=False, compile_workers=0, force=False):
    """Extract everything in site-packages to a specified path.

    :param ZipFile archive: The zipfile object we are bootstrapping from.
    :param Path target_path: The path to extract our zip to.
    :param bool compile_pyc: A boolean to dictate whether we pre-compile pyc.
    :param int compile_workers: An int representing the number of pyc compiler workers.
    :param bool force: A boolean to dictate whether or not we force extraction.
    """
    parent = target_path.parent
    target_path_tmp = Path(parent, target_path.name + ".tmp")
    lock = Path(parent, f".{target_path.name}_lock")

    # If this is the first time that a pyz is being extracted, we'll need to create the ~/.shiv dir
    if not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)

    with FileLock(lock):

        # we acquired a lock, it's possible that prior invocation was holding the lock and has
        # completed bootstrapping, so let's check (again) if we need to do any work
        if not target_path.exists() or force:

            # extract our site-packages
            for fileinfo in archive.infolist():

                if fileinfo.filename.startswith("site-packages"):
                    extracted = archive.extract(fileinfo.filename, target_path_tmp)

                    # restore original permissions
                    os.chmod(extracted, fileinfo.external_attr >> 16)

            if compile_pyc:
                compileall.compile_dir(target_path_tmp, quiet=2, workers=compile_workers)

            # if using `force` we will need to delete our target path
            if target_path.exists():
                shutil.rmtree(str(target_path))

            # atomic move
            shutil.move(str(target_path_tmp), str(target_path))


def get_first_sitedir_index():
    for index, part in enumerate(sys.path):
        if Path(part).stem in ("site-packages", "dist-packages"):
            return index


def extend_python_path(environ, additional_paths):
    """Create or extend a PYTHONPATH variable with the frozen environment we are bootstrapping with."""

    # we don't want to clobber any existing PYTHONPATH value, so check for it.
    python_path = environ["PYTHONPATH"].split(os.pathsep) if "PYTHONPATH" in environ else []
    python_path.extend(additional_paths)

    # put it back into the environment so that PYTHONPATH contains the shiv-manipulated paths
    # and any pre-existing PYTHONPATH values with no duplicates.
    environ["PYTHONPATH"] = os.pathsep.join(sorted(set(python_path), key=python_path.index))


def ensure_no_modify(site_packages, hashes):
    """Compare the sha256 hash of the unpacked source files to the files when they were added to the pyz."""

    for path in site_packages.rglob("**/*.py"):

        if hashlib.sha256(path.read_bytes()).hexdigest() != hashes.get(str(path.relative_to(site_packages))):
            raise RuntimeError(
                "A Python source file has been modified! File: {}. "
                "Try again with SHIV_FORCE_EXTRACT=1 to overwrite the modified source file(s).".format(str(path))
            )


def bootstrap():  # pragma: no cover
    """Actually bootstrap our shiv environment."""

    # get a handle of the currently executing zip file
    with current_zipfile() as archive:

        # create an environment object (a combination of env vars and json metadata)
        env = Environment.from_json(archive.read("environment.json").decode())

        # get a site-packages directory (from env var or via build id)
        site_packages = cache_path(archive, env.root, env.build_id) / "site-packages"

        # determine if first run or forcing extract
        if not site_packages.exists() or env.force_extract:
            extract_site_packages(
                archive,
                site_packages.parent,
                env.compile_pyc,
                env.compile_workers,
                env.force_extract,
            )

    # get sys.path's length
    length = len(sys.path)

    # Find the first instance of an existing site-packages on sys.path
    index = get_first_sitedir_index() or length

    # append site-packages using the stdlib blessed way of extending path
    # so as to handle .pth files correctly
    site.addsitedir(site_packages)

    # reorder to place our site-packages before any others found
    sys.path = sys.path[:index] + sys.path[length:] + sys.path[index:length]

    # check if source files have been modified, if required
    if env.no_modify:
        ensure_no_modify(site_packages, env.hashes)

    # add our site-packages to the environment, if requested
    if env.extend_pythonpath:
        extend_python_path(os.environ, sys.path.copy())

    # if a preamble script was provided, run it
    if env.preamble:

        # path to the preamble
        preamble_bin = site_packages / "bin" / env.preamble

        if preamble_bin.suffix == ".py":
            runpy.run_path(
                str(preamble_bin),
                init_globals={"archive": sys.argv[0], "env": env, "site_packages": site_packages},
                run_name="__main__",
            )

        else:
            subprocess.run([preamble_bin])

    # first check if we should drop into interactive mode
    if not env.interpreter:

        # do entry point import and call
        if env.entry_point is not None and not env.script:
            run(import_string(env.entry_point))

        elif env.script is not None:
            run(partial(runpy.run_path, str(site_packages / "bin" / env.script), run_name="__main__"))

    # all other options exhausted, drop into interactive mode
    execute_interpreter()


if __name__ == "__main__":
    bootstrap()
