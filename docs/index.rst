shiv 🔪
====================

Shiv is a command line utility for building fully self-contained Python zipapps as outlined in `PEP 441 <http://legacy.python.org/dev/peps/pep-0441/>`_
but with all their dependencies included!

Shiv's primary goal is making distributing Python applications fast & easy.

How it works
------------

Internally, shiv includes two major components: a *builder* and a small *bootstrap* runtime.

Building
^^^^^^^^

In order to build self-contained, single-artifact executables, shiv leverages ``pip`` to stage your project's dependencies
and then uses the features described in `PEP 441 <http://legacy.python.org/dev/peps/pep-0441/>`_ to create a "zipapp".

The primary feature of PEP 441 that ``shiv`` uses is Python's ability to implicitly execute a `__main__.py` file inside of a zip archive.
Here's an example of the feature in action:

.. code-block:: sh

    $ echo "print('hello world')" >> __main__.py
    $ zip archive.zip __main__.py
    adding: __main__.py (stored 0%)
    $ python3 ./archive.zip
    hello world

``shiv`` expands on this functionality by packing your dependencies into the same zip and adding a specialized `__main__.py` that instructs the Python interpreter to
unpack those dependencies to a known location. Then, at runtime, adds those dependencies to your interpreter's search path, and that's it!

.. note::
    "Conventional" zipapps don't include any dependencies, which is what sets shiv apart from the stdlib zipapp module.

``shiv`` accepts only a few command line parameters of its own, `described here <cli-reference.html>`_, and under the covers, **any unprocessed parameters are
delegated to** ``pip install``. This allows users to fully leverage all the functionality that pip provides.

For example, if you wanted to create an executable for ``flake8``, you'd specify the required
dependencies (in this case, simply ``flake8``), the callable (either via ``-e`` for a setuptools-style entry
point or ``-c`` for a bare console_script name), and the output file:

.. code-block:: sh

    $ shiv -c flake8 -o ~/bin/flake8 flake8

Let's break this command down,

* ``shiv`` is the command itself.
* ``-c flake8`` specifies the ``console_script`` for flake8 (`defined here <https://github.com/PyCQA/flake8/blob/3.9.2/setup.cfg#L61-L62>`_)
* ``-o ~/bin/flake8`` specifies the ``outfile``
* ``flake8`` is a dependency (this portion of the command is delegated to ``pip install``)

This creates an executable (``~/bin/flake8``) containing all the dependencies specified (``flake8``)
that, when invoked, executes the provided console_script (``flake8``)!

If you were to omit the entry point/console script flag, invoking the resulting executable would drop you into an interpreter that
is bootstrapped with the dependencies you've specified. This can be useful for creating a single-artifact executable
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

This is particularly useful for running scripts without needing to create a virtual environment or contaminate your Python
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

As mentioned above, when you run an executable created with ``shiv``, a special bootstrap function is called.
This function unpacks the dependencies into a uniquely named subdirectory of ``~/.shiv`` and then runs your entry point
(or interactive interpreter) with those dependencies added to your interpreter's search path (``sys.path``).

To improve performance, once the dependencies have been extracted to disk, any further invocations will re-use the 'cached'
site-packages unless they are deleted or moved.

.. note::

    Dependencies are extracted (rather than loaded into memory from the zipapp itself) for two reasons.

    **1.) Because of limitations of third-party and binary dependencies.**

    Just as an example, shared objects loaded via the dlopen syscall require a regular filesystem.
    In addition, many libraries also expect a filesystem in order to do things like building paths via ``__file__`` (which doesn't work when a module is imported from a zip), etc.
    To learn more, check out this resource about the setuptools `"zip_safe" flag <https://setuptools.pypa.io/en/latest/userguide/miscellaneous.html#setting-the-zip-safe-flag>`_.

    **2.) Performance reasons**

    Decompressing files takes time, and if we loaded the dependencies from the zip file every time it would significantly slow down invocation speed.

Preamble
^^^^^^^^

As an application packager, you may want to run some sanity checks or clean up tasks when users execute a pyz.
For such a use case, ``shiv`` provides a ``--preamble`` flag.
Any executable script passed to that flag will be packed into the zipapp and invoked during bootstrapping (*after* extracting dependencies but *before* invoking an entry point / console script).

If the preamble file is written in Python (e.g. ends in ``.py``) then shiv will inject three variables into the runtime that may be useful to preamble authors:

* ``archive``: (a string) path to the current PYZ file
* ``env``: an instance of the `Environment <api:bootstrap.environment.Environment>`_ object.
* ``site_packages``: a :py:class:`pathlib.Path` of the directory where the current PYZ's site_packages were extracted to during bootstrap.

For an example, a preamble file that cleans up prior extracted ``~/.shiv`` directories might look like:

.. code-block:: py

    #!/usr/bin/env python3

    import shutil

    from pathlib import Path

    # These variables are injected by shiv.bootstrap
    site_packages: Path
    env: "shiv.bootstrap.environment.Environment"

    # Get a handle of the current PYZ's site_packages directory
    current = site_packages.parent

    # The parent directory of the site_packages directory is our shiv cache
    cache_path = current.parent


    name, build_id = current.name.split('_')

    if __name__ == "__main__":
        for path in cache_path.iterdir():
            if path.name.startswith(f"{name}_") and not path.name.endswith(build_id):
                shutil.rmtree(path)

Hello World
^^^^^^^^^^^

Here's an example of how to set up a hello-world executable using ``shiv``.

First, create a new project:

.. code-block:: sh

    $ mkdir hello-world
    $ cd hello-world

Add some code.

.. code-block:: python
   :caption: hello.py

    def main():
        print("Hello world")

    if __name__ == "__main__":
        main()

Second, create a Python package using your preferred workflow (for this example, I'll simply create a minimal ``setup.py`` file).

.. code-block:: python
   :caption: setup.py

    from setuptools import setup

    setup(
        name="hello-world",
        version="0.0.1",
        description="Greet the world.",
        py_modules=["hello"],
        entry_points={
            "console_scripts": ["hello=hello:main"],
        },
    )

That's it! We now have a proper Python package, so we can use ``shiv`` to create a single-artifact executable for it.

.. code-block:: sh

    $ shiv -c hello -o hello .

.. note::

   Notice the ``.`` at the end of the ``shiv`` invocation. That is referring to the local package that we just created.
   You can think of it as analogous to running ``pip install .``

That's it! Our example should now execute as expected.

.. code-block:: sh

    $ ./hello
    Hello world

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

SHIV_ENTRY_POINT / SHIV_MODULE
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note:: Same functionality as ``-e/--entry-point`` at build time

This should be populated with a setuptools-style callable, e.g. "module.main:main". This will
execute the pyz with whatever callable entry point you supply. Useful for sharing a single pyz
across many callable 'scripts'.

SHIV_CONSOLE_SCRIPT
^^^^^^^^^^^^^^^^^^^

.. note:: Same functionality as ``-c/--console-script` at build time

Similar to the SHIV_ENTRY_POINT and SHIV_MODULE environment variables, SHIV_CONSOLE_SCRIPT overrides any value
provided at build time.

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
