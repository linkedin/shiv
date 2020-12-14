shiv 🔪
====================

Shiv is a command line utility for building fully self-contained Python zipapps as outlined in `PEP 441 <http://legacy.python.org/dev/peps/pep-0441/>`_
but with all their dependencies included!

Shiv's primary goal is making distributing Python applications fast & easy.

How it works
------------

Shiv includes two major components: a *builder* and a small *bootstrap* runtime.

Building
^^^^^^^^

In order to build self-contained single-artifact executables, shiv leverages ``pip`` to stage your project's dependencies
and then shiv uses the features described in `PEP 441 <http://legacy.python.org/dev/peps/pep-0441/>`_ to create a "zipapp".

The feature of PEP 441 we are using is Python's ability to implicitly execute a `__main__.py` file inside of a zip archive.
Shiv packs your dependencies into a zip and then adds a special `__main__.py` file that instructs the Python interpreter to
unpack those dependencies to a known location, add them to your interpreter's search path, and that's it!

.. note::
    "Conventional" zipapps don't include any dependencies, which is what sets shiv apart from the stdlib zipapp module.

shiv accepts only a few command line parameters of its own, `described here <cli-reference.html>`_, and any unprocessed parameters are
delegated to ``pip install``. This allows users to fully leverage all the functionality that pip provides.

For example, if you wanted to create an executable for ``flake8``, you'd specify the required
dependencies (in this case, simply ``flake8``), the callable (either via ``-e`` for a setuptools-style entry
point or ``-c`` for a bare console_script name), and the output file:

.. code-block:: sh

    $ shiv -c flake8 -o ~/bin/flake8 flake8

This creates an executable (``~/bin/flake8``) containing all the dependencies required by
``flake8`` that invokes the console_script ``flake8`` when executed!

You can optionally omit the entry point specification, which will drop you into an interpreter that
is bootstrapped with the dependencies you specify. This can be useful for creating a single-artifact executable
Python environment:

.. code-block:: sh

    $ shiv httpx -o httpx.pyz --quiet
    $ ./httpx.pyz
    Python 3.7.7 (default, Mar 10 2020, 16:11:21)
    [Clang 11.0.0 (clang-1100.0.33.12)] on darwin
    Type "help", "copyright", "credits" or "license" for more information.
    (InteractiveConsole)
    >>> import httpx
    >>> httpx.get("https://shiv.readthedocs.io")
    <Response [200 OK]>

This is particularly useful for running scripts without needing to contaminate your Python
environment, since the ``pyz`` files can be used as a shebang!

.. code-block:: sh

    $ cat << EOF > tryme.py
    > #!/usr/bin/env httpx.pyz
    >
    > import httpx
    > url = "https://shiv.readthedocs.io"
    > response = httpx.get(url)
    > print(f"Got {response.status_code} from {url}!")
    >
    > EOF
    $ chmod +x tryme.py
    $ ./tryme.py
    Got 200 from https://shiv.readthedocs.io!

Bootstrapping
^^^^^^^^^^^^^

As mentioned above, when you run an executable created with shiv, a special bootstrap function is called.
This function unpacks dependencies into a uniquely named subdirectory of ``~/.shiv`` and then runs your entry point
(or interactive interpreter) with those dependencies added to your interpreter's search path (``sys.path``).
To improve performance, once the dependencies have been extracted to disk, any further invocations will re-use the 'cached'
site-packages unless they are deleted or moved.

.. note::

    Dependencies are extracted (rather than loaded into memory from the zipapp itself) because of
    limitations of binary dependencies. Just as an example, shared objects loaded via the dlopen syscall
    require a regular filesystem.
    Many libraries also expect a filesystem in order to do things like building paths via ``__file__`` (which
    doesn't work when a module is imported from a zip), etc.
    To learn more, check out this resource about the setuptools `"zip_safe" flag <https://setuptools.readthedocs.io/en/latest/setuptools.html#setting-the-zip-safe-flag/>`_.

Influencing Runtime
-------------------

Whenever you are creating a zipapp with ``shiv``, you can specify a few flags that influence the runtime.
For example, the ``-c/--console-script`` and ``-e/--entry-point`` options already mentioned in this doc.
To see the full list of command line options, see this page.

In addition to options that are settable during zipapp creation, there are a number of environment variables
you can specify to influence a zipapp created with shiv at run time.

SHIV_ROOT
^^^^^^^^^

This should be populated with a full path, it overrides ``~/.shiv`` as the default base dir for shiv's extraction cache.

This is useful if you want to collect the contents of a zipapp to inspect them, or if you want to make a quick edit to
a source file, but don't want to taint the extraction cache.

SHIV_INTERPRETER
^^^^^^^^^^^^^^^^

This is a boolean that bypasses and console_script or entry point baked into your pyz. Useful for
dropping into an interactive session in the environment of a built cli utility.

SHIV_ENTRY_POINT
^^^^^^^^^^^^^^^^

.. note:: Same functionality as ``-e/--entry-point`` at build time

This should be populated with a setuptools-style callable, e.g. "module.main:main". This will
execute the pyz with whatever callable entry point you supply. Useful for sharing a single pyz
across many callable 'scripts'.

SHIV_FORCE_EXTRACT
^^^^^^^^^^^^^^^^^^

This forces re-extraction of dependencies even if they've already been extracted. If you make
hotfixes/modifications to the 'cached' dependencies, this will overwrite them.

SHIV_EXTEND_PYTHONPATH
^^^^^^^^^^^^^^^^^^^^^^

.. note:: Same functionality as ``-E/--extend-pythonpath`` at build time.

This is a boolean that adds the modules bundled into the zipapp into the ``PYTHONPATH`` environment
variable. It is not needed for most applications, but if an application calls Python as a
subprocess, expecting to be able to import the modules bundled in the zipapp, this will allow it
to do so successfully.

Preamble
^^^^^^^^

As an application packager, you may want to run some sanity checks or clean up tasks when users execute
a pyz. For such a use case, ``shiv`` provides a ``--preamble`` argument. Any executable script provided will be packed
into the resulting zipapp and executed during bootstrapping.

If the preamble file is written in Python (e.g. ends in ``.py``) then shiv will inject two variables into the runtime
that may be useful to preamble authors:

* ``archive``: path to the current PYZ file, equivalent to ``sys.argv[0]``
* ``env``: an instance of the :ref:`Environment <api:bootstrap.environment.Environment>` object.
* ``site_packages``: a pathlib.Path of the directory where the current PYZ's site_packages were extracted to during bootsrap.

For an example, a preamble file that cleans up prior extracted ``~/.shiv`` directories might look like::

    #!/usr/bin/env python3

    import shutil

    from pathlib import Path

    # variable injected from shiv.bootstrap
    site_packages: Path

    current = site_packages.parent
    cache_path = current.parent
    name, build_id = current.name.split('_')

    if __name__ == "__main__":
        for path in cache_path.iterdir():
            if path.name.startswith(f"{name}_") and not path.name.endswith(build_id):
                shutil.rmtree(path)

Reproducibility
^^^^^^^^^^^^^^^

``shiv`` supports the ability to create reproducible artifacts. By using the ``--reproducible`` command line option or
by setting the ``SOURCE_DATE_EPOCH`` environment variable during zipapp creation. When this option is selected, if the
inputs do not change, the output should be idempotent.

For more information, see https://reproducible-builds.org/.

Table of Contents
=================

.. toctree::
   :maxdepth: 2

   cli-reference
   history
   api
   django

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
