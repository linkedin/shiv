import datetime
import sys
import os

from pathlib import Path

here = Path(__file__).parent
sys.path.insert(0, str(Path(here.parent, 'src')))

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode']
source_suffix = '.rst'
master_doc = 'index'
project = u'shiv'
copyright = u"{year}, LinkedIn".format(year=datetime.datetime.now().year)
pygments_style = 'sphinx'
html_theme = 'default'
