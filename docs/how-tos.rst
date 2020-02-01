**********************
How-Tos, Tips & Tricks
**********************

This chapter contains some practical examples of using ``shiv`` in the real world,
to give you a better idea how it can fit into your projects
and their deployment workflows.


Shipping Dependency Sets as a Single File
=========================================

If you have a bunch of Python scripts that are all using the same set of base libraries,
you can distribute those dependencies in the form of a zipapp,
i.e. in a single executable file.
This way, you can have a project for the base libraries
and other projects for the scripts,
including scripts written by your end users.

The following example uses ``shiv`` itself for demonstration purposes,
you'd use a setuptools project defining the needed dependencies
when applying this ‘for real’.

So, to create your base library release artifact, call
``shiv`` like this in your project's workdir::

    PROJECT=shiv
    shiv -p '/usr/bin/python3.6 -IS' -o ~/bin/_lib-$PROJECT .

Note that we do not provide an entry point here, which means this zipapp
drops into the given Python interpreter and is thus usable *as* an
interpeter, but with the dependencies of the project added.

The ``-IS`` options in ``-p`` ensure this zipapp runs isolated (for increased security),
with neither the current working directory
nor the host's site packages in the Python path.

.. tip::

    Replace the ``.`` at the end of the ``shiv`` call
    by a literal list of PyPI packages,
    or load them from a requirements file (``-r lib-requirements.txt``),
    and you don't need an extra project for getting your base set defined.

Now we can exploit this to write a script using the zipapp as its interpreter::

    cat >script <<'.'
    #! /usr/bin/env _lib-shiv
    import sys
    from pathlib import Path
    import shiv

    print('Imported shiv from',
          Path(shiv.__file__).parent,
          '\nPython path:',
          '\n'.join(sys.path),
          sep='\n')
    .
    chmod +x script
    ./script

Calling the script produces the following output::

    Imported shiv from
    /home/user/.shiv/_lib-shiv_8a…e9/site-packages/shiv

    Python path:
    /home/user/bin/_lib-shiv
    /usr/lib/python36.zip
    /usr/lib/python3.6
    /usr/lib/python3.6
    /usr/lib/python3.6/lib-dynload
    /home/user/.shiv/_lib-shiv_8a…e9/site-packages

The underscore prefix in the zipapp name indicates this is not a command
humans would normally use – alternatively you can deploy into e.g.
``/usr/local/lib/python3.6/`` and then use an absolute path instead of
an ``env`` call in the script's shebang.


External Resources
==================

Here are some links to related articles on the web.

* `Enabling Easy Zipapp Installs on Windows`_ – Describes the required steps to make zipapps really shine on Windows (i.e. make them work pretty much like on POSIX systems).


.. _`Enabling Easy Zipapp Installs on Windows`: https://py-generic-project.readthedocs.io/en/latest/installing.html#enabling-easy-zipapp-installs-on-windows
