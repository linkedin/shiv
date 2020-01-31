**********************
Complete CLI Reference
**********************

This is a full reference of the project's command line tools,
with the same information as you get from using the :option:`-h` option.
It is generated from source code and thus always up to date.


Available Commands
==================

.. contents::
   :local:

.. click:: shiv.cli:main
   :prog: shiv
   :show-nested:

.. click:: shiv.info:main
   :prog: shiv-info
   :show-nested:


Additional Hints
================

Choosing a Python Interpreter Path
----------------------------------

A good overall interpreter path as passed into :option:`--python` is ``/usr/bin/env python3``.
If you want to make sure your code runs on the Python version you tested it on,
include the minor version (e.g. ``… python3.6``) – use what fits your circumstances best.

On Windows, the Python launcher ``py`` knows how to handle shebangs using ``env``,
so it's overall the best choice if you target multiple platforms with a pure Python zipapp.

Also note that you can always fix the shebang during installation of a zipapp using this:

.. code-block:: shell

   python3 -m zipapp -p '/usr/bin/env python3.7' -o ~/bin/foo foo.pyz
