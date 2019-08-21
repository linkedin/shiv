import sys

if sys.version_info < (3, 6):
    print('\nshiv requires at least Python 3.6!')
    sys.exit(1)

import os
import re
import setuptools
import venv

from pathlib import Path
from setuptools.command import easy_install

# The following template and classmethod are copied from
# fast entry points, Copyright (c) 2016, Aaron Christianson
# https://github.com/ninjaaron/fast-entry_point

TEMPLATE = '''\
# -*- coding: utf-8 -*-
# EASY-INSTALL-ENTRY-SCRIPT: '{3}','{4}','{5}'
__requires__ = '{3}'
import re
import sys
from {0} import {1}
if __name__ == '__main__':
    sys.argv[0] = re.sub(r'(-script\.pyw?|\.exe)?$', '', sys.argv[0])
    sys.exit({2}())'''


@classmethod
def get_args(cls, dist, header=None):
    """Overrides easy_install.ScriptWriter.get_args

    This method avoids using pkg_resources to map a named entry_point
    to a callable at invocation time.
    """
    if header is None:
        header = cls.get_header()
    spec = str(dist.as_requirement())
    for type_ in 'console', 'gui':
        group = type_ + '_scripts'
        for name, ep in dist.get_entry_map(group).items():
            # ensure_safe_name
            if re.search(r'[\\/]', name):
                raise ValueError("Path separators not allowed in script names")
            script_text = TEMPLATE.format(
                ep.module_name,
                ep.attrs[0],
                '.'.join(ep.attrs),
                spec,
                group,
                name,
            )
            args = cls._get_script_args(type_, name, header, script_text)
            for res in args:
                yield res

# patch in the fast-entry_points classmethod
easy_install.ScriptWriter.get_args = get_args

# fast entry points end.


class Venv(setuptools.Command):
    user_options = []

    def initialize_options(self):
        """Abstract method that is required to be overwritten"""

    def finalize_options(self):
        """Abstract method that is required to be overwritten"""

    def run(self):
        venv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'venv', 'shiv')
        print('Creating virtual environment in {}'.format(venv_path))
        venv.main(args=[venv_path])
        print(
            'Linking `activate` to top level of project.\n'
            'To activate, simply run `source activate`.'
        )
        try:
            os.symlink(
                Path(venv_path, 'bin', 'activate'),
                Path(Path(__file__).absolute().parent, 'activate'),
            )
        except FileExistsError:
            pass


setuptools.setup(
    cmdclass={'venv': Venv},
)
