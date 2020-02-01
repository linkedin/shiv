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

If you have ``coreutils`` with at least version 8.30 on your Linux system,
then you can use env shebangs *and* pass argument to Python, like in this example:

.. code-block:: shell

    shiv -p '/usr/bin/env -S python3 -I -S' …

The magic ingredient is the new ``-S`` (split) option, but as of 2020
you have to target very new stable releases like Debian Buster
or rolling distributions for it to actually work.
Check for the option by calling ``env --help``.

Also note that you can always fix the shebang during installation of a zipapp using this:

.. code-block:: shell

   python3 -m zipapp -p '/usr/bin/env python3.7' -o ~/bin/foo foo.pyz
