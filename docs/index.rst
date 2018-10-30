shiv 🔪
====================

Shiv is a command line utility for building fully self
contained Python zipapps as outlined in `PEP 441 <http://legacy.python.org/dev/peps/pep-0441/>`_
but with all their dependencies included!

Shiv's primary goal is making distributing Python applications fast & easy.

How it works
------------

Shiv includes two major components: a *builder* and a *bootstrap* module.

Building
^^^^^^^^

In order to build self-contained single-artifact executables, shiv leverages ``pip`` and stdlib's
``zipapp`` module.

.. note::
    Unlike "conventional" zipapps, shiv packs a site-packages style directory of your tool's
    dependencies into the resulting binary, and then at bootstrap time extracts it into a ``~/.shiv``
    cache directory. More on this in the `Bootstrapping` section.

shiv accepts only a few command line parameters of it's own, and any unprocessed parameters are
delegated to ``pip install``.

For example, if you wanted to create an executable for Pipenv, you'd specify the required
dependencies (``pipenv`` and ``pew``), the callable (either ``-e`` for a setuptools-style entry
point or ``-c`` for a bare console_script name), and the output file.

.. code-block:: sh

    $ shiv -c pipenv -o ~/bin/pipenv pipenv pew

This creates an executable (``~/bin/pipenv``) containing all the dependencies required by
``pipenv`` and ``pew`` that invokes the console_script ``pipenv`` when executed!

You can optionally omit the entry point specification, which will drop you into an interpreter that
is bootstrapped with the dependencies you specify.

.. code-block:: sh

    $ shiv requests -o requests.pyz --quiet
    $ ./requests.pyz
    Python 3.6.1 (default, Apr 19 2017, 15:02:08)
    [GCC 4.2.1 Compatible Apple LLVM 7.3.0 (clang-703.0.29)] on darwin
    Type "help", "copyright", "credits" or "license" for more information.
    (InteractiveConsole)
    >>> import requests
    >>> requests.get('http://shiv.readthedocs.io/')
    <Response [200]>

This is particularly useful for running scripts without needing to contaminate your Python
environment, since the ``pyz`` files can be used as a shebang!

Bootstrapping
^^^^^^^^^^^^^

When you run an executable created with shiv a special bootstrap function is called. This function
unpacks dependencies into a uniquely named subdirectory of ``~/.shiv`` and then runs your entry point
(or interactive interpreter) with those dependencies added to your ``sys.path``. Once the
dependencies have been extracted to disk, any further invocations will re-use the 'cached'
site-packages unless they are deleted or moved.

.. note::

    Dependencies are extracted (rather than loaded into memory from the zipapp itself) because of
    limitations of binary dependencies. Shared objects loaded via the dlopen syscall require a
    regular filesystem. Many libraries also expect a filesystem in order to do things like building
    paths via ``__file__``, etc.

Influencing Runtime
-------------------

There are a number of environment variables you can specify to influence a `pyz` file created with
shiv.

SHIV_ROOT
^^^^^^^^^

This should be populated with a full path, it effectively overrides ``~/.shiv`` as the default base
dir for shiv's extraction cache.

SHIV_INTERPRETER
^^^^^^^^^^^^^^^^

This is a boolean that bypasses and console_script or entry point baked into your pyz. Useful for
dropping into an interactive session in the environment of a built cli utility.

SHIV_ENTRY_POINT
^^^^^^^^^^^^^^^^

This should be populated with a setuptools-style callable, e.g. "module.main:main". This will
execute the pyz with whatever callable entry point you supply. Useful for sharing a single pyz
across many callable 'scripts'.

SHIV_FORCE_EXTRACT
^^^^^^^^^^^^^^^^^^

This forces re-extraction of dependencies even if they've already been extracted. If you make
hotfixes/modifications to the 'cached' dependencies, this will overwrite them.

SHIV_EXTEND_PYTHONPATH
^^^^^^^^^^^^^^^^^^^^^^

This is a boolean that adds the modules bundled into the zipapp into the ``PYTHONPATH`` environment
variable. It is not needed for most applications, but if an application calls Python as a
subprocess, expecting to be able to import the modules bundled in the zipapp, this will allow it
to do so successfully.

Table of Contents
=================

.. toctree::
   :maxdepth: 2

   history
   api
   django

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
