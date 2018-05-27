Motivation & Comparisons
========================

Why?
----

At LinkedIn we ship hundreds of command line utilities to every machine in our data-centers and all
of our employees workstations. The vast majority of these utilties are written in Python. In
addition to these utilities we also have many internal libraries that are uprev'd daily.

Because of differences in iteration rate and the inherent problems present when dealing with such a
huge dependency graph, we need to package the executables discretely. Initially we took advantage
of the great open source tool `PEX <https://github.com/pantsbuild/pex>`_. PEX elegantly solved the
isolated packaging requirement we had by including all of a tool's dependencies inside of a single
binary file that we could then distribute!

However, as our tools matured and picked up additional dependencies, we became acutely aware of the
performance issues being imposed on us by ``pkg_resources``'s
`Issue 510 <https://github.com/pypa/setuptools/issues/510>`_. Since PEX leans heavily on
``pkg_resources`` to bootstrap it's environment, we found ourselves at an impass: lose out on the
ability to neatly package our tools in favor of invocation speed, or impose a few second
performance penalty for the benefit of easy packaging.

After spending some time investigating extricating pkg_resources from PEX, we decided to start from
a clean slate and thus ``shiv`` was created.

How?
----

Shiv exploits the same features of Python as PEX, packing ``__main__.py`` into a zipfile with a
shebang prepended (akin to zipapps, as defined by
`PEP 441 <https://www.python.org/dev/peps/pep-0441/>`_, extracting a dependency directory and
injecting said dependencies at runtime. We have to credit the great work by @wickman, @kwlzn,
@jsirois and the other PEX contributors for laying the groundwork!

The primary differences between PEX and shiv are:

* ``shiv`` completely avoids the use of ``pkg_resources``. If it is included by a transitive
  dependency, the performance implications are mitigated by limiting the length of ``sys.path``.
  Internally, at LinkedIn, we always include the
  `-s <https://docs.python.org/3/using/cmdline.html#cmdoption-s>`_ and
  `-E <https://docs.python.org/3/using/cmdline.html#cmdoption-e>`_ Python interpreter flags by
  specifying ``--python "/path/to/python -sE"``, which ensures a clean environment.
* Instead of shipping our binary with downloaded wheels inside, we package an entire site-packages
  directory, as installed by ``pip``. We then bootstrap that directory post-extraction via the
  stdlib's ``site.addsitedir`` function. That way, everything works out of the box: namespace
  packages, real filesystem access, etc.

Because we optimize for a shorter ``sys.path`` and don't include ``pkg_resources`` in the critical
path, executables created with ``shiv`` can outperform ones created with PEX by almost 2x. In most
cases the executables created with ``shiv`` are even faster than running a script from within a
virtualenv!
