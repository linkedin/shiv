import datetime
import sys

from pathlib import Path

here = Path(__file__).parent
sys.path.insert(0, str(Path(here.parent, 'src').absolute()))

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode', 'sphinx_click.ext', 'sphinx.ext.intersphinx']
source_suffix = '.rst'
master_doc = 'index'
project = u'shiv'
# noinspection PyShadowingBuiltins
copyright = u"{year}, LinkedIn".format(year=datetime.datetime.now().year)
pygments_style = 'sphinx'
html_theme = 'default'
intersphinx_mapping = {'python': ('https://docs.python.org/3', None)}
