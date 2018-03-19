import os
import site
import sys

from importlib import import_module
from importlib.machinery import ExtensionFileLoader, ModuleSpec
from pathlib import Path

from .environment import Environment
from .interpreter import execute_interpreter
from .utils import current_zipfile


class SOFinder:
    def __init__(self, so_map, cache_root, archive):
        self.so_map = so_map
        self.cache_root = cache_root
        self.archive = archive

    def find_spec(self, name, paths, module=None):
        origin = self.so_map.get(name)

        if origin is None:
            return None

        extracted_path = Path(self.cache_root) / origin

        if not extracted_path.exists():
            self.archive.extract(origin, self.cache_root)

        loader = ExtensionFileLoader(name, extracted_path)

        return ModuleSpec(name, loader, origin=extracted_path)


def import_string(import_name):
    """Returns a callable for a given setuptools style import string

    :param import_name: A console_scripts style import string
    """
    import_name = str(import_name).replace(':', '.')
    try:
        import_module(import_name)
    except ImportError:
        if '.' not in import_name:
            # this is a case like "import name", where continuing to the
            # next style of import would not improve the situation, so
            # we raise here.
            raise
    else:
        return sys.modules[import_name]

    # this is a case where the previous attempt may have failed due to
    # not being importable. ("not a package", etc)
    module_name, obj_name = import_name.rsplit('.', 1)
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


def process_zipped_pths(archive, sitedir):
    """Similar to site.addpackage, but for zipped site-packages.

    :param ZipFile archive: The zipfile object we are bootstrapping from.
    :param str sitedir: The site-packages directory inside the zip.
    """
    known_paths = set()
    pths = [f for f in archive.namelist() if f.endswith(os.extsep + 'pth')]
    for pth in pths:
        pth_lines = archive.read(pth).decode().splitlines()
        for line in pth_lines:
            if line.startswith("#"):
                continue
            if line.startswith(("import ", "import\t")):
                exec(line)
                continue
            line = line.rstrip()
            dir, dircase = site.makepath(sitedir, line)
            if dircase not in known_paths and Path(dir).exists():
                sys.path.append(dir)
                known_paths.add(dircase)


def cache_path(archive, build_id):
    """Returns a ~/.shiv cache directory for unzipping site-packages during bootstrap.

    :param ZipFile archive: The zipfile object we are bootstrapping from.
    :param str buidl_id: The build id generated at zip creation.
    """
    dot_shiv = Path('~/.shiv').expanduser()
    name = Path(archive.filename).stem
    return dot_shiv / f"{name}_{build_id}"


def extract_site_packages(archive, target_path):
    """Extract everything in site-packages to a specified path.

    :param ZipFile archive: The zipfile object we are bootstrapping from.
    :param str target_path: The path to extract our zip to.
    """
    for filename in archive.namelist():
        if filename.startswith('site-packages'):
            archive.extract(filename, target_path)


def bootstrap():
    """Actually bootstrap our shiv environment."""

    # get a handle of the currently executing zip file
    archive = current_zipfile()

    # create an environment object (a combination of env vars and json metadata)
    env = Environment.from_json(archive.read('environment.json').decode())

    # get a site-packages directory (from env var or via build id)
    site_packages = env.site_packages or cache_path(archive, env.build_id)

    if env.zip_safe is True:
        # add shared object finder
        finder = SOFinder(env.shared_object_map, site_packages, archive)
        sys.meta_path.insert(0, finder)

        # process pth files
        process_zipped_pths(archive, site_packages)

        # add the zipped site-packages to sys.path
        sys.path.append(Path(archive.filename, 'site-packages'))

    else:
        # determine if first run or forcing extract
        if not site_packages.exists() or env.force_extract:
            extract_site_packages(archive, site_packages)

        # stdlib blessed way of extending path
        site.addsitedir(site_packages / 'site-packages')

    # do entry point import and call
    if env.entry_point is not None and env.interpreter is None:
        mod = import_string(env.entry_point)
        try:
            mod()
        except TypeError as e:
            # catch "<module> is not callable", which is thrown when the entry point's
            # callable shares a name with it's parent module
            # e.g. "from foo.bar import bar; bar()"
            getattr(mod, env.entry_point.replace(':', '.').split('.')[1])()
    else:
        # drop into interactive mode
        execute_interpreter()


if __name__ == '__main__':
    bootstrap()
