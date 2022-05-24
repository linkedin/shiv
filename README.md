[![pypi](https://img.shields.io/pypi/v/shiv.svg)](https://pypi.python.org/pypi/shiv)
[![ci](https://github.com/linkedin/shiv/workflows/ci/badge.svg)](https://github.com/linkedin/shiv/actions?query=workflow%3Aci)
[![codecov](https://codecov.io/gh/linkedin/shiv/branch/master/graph/badge.svg)](https://codecov.io/gh/linkedin/shiv)
[![docs](https://readthedocs.org/projects/shiv/badge/?version=latest)](http://shiv.readthedocs.io/en/latest/?badge=latest)
[![license](https://img.shields.io/badge/License-BSD%202--Clause-orange.svg)](https://opensource.org/licenses/BSD-2-Clause)
[![supported](https://img.shields.io/pypi/pyversions/shiv.svg)](https://pypi.python.org/pypi/shiv)

![snake](https://github.com/linkedin/shiv/raw/main/logo.png)

# shiv
shiv is a command line utility for building fully self-contained Python zipapps as outlined in [PEP 441](https://www.python.org/dev/peps/pep-0441/), but with all their dependencies included!

shiv's primary goal is making distributing Python applications fast & easy.

📗 Full documentation can be found [here](http://shiv.readthedocs.io/en/latest/).

### sys requirements

- python3.6+
- linux/osx/windows

### quickstart

shiv has a few command line options of its own and accepts almost all options passable to `pip install`.

##### simple cli example

Creating an executable of flake8 with shiv:

```sh
$ shiv -c flake8 -o ~/bin/flake8 flake8
$ ~/bin/flake8 --version
3.7.8 (mccabe: 0.6.1, pycodestyle: 2.5.0, pyflakes: 2.1.1) CPython 3.7.4 on Darwin
```

`-c flake8` specifies the console script that should be invoked when the executable runs, `-o ~/bin/flake8` specifies the location of the generated executable file and `flake8` is the dependency that should be installed from PyPI.

Creating an interactive executable with the boto library:

```sh
$ shiv -o boto.pyz boto
Collecting boto
Installing collected packages: boto
Successfully installed boto-2.49.0
$ ./boto.pyz
Python 3.7.4 (v3.7.4:e09359112e, Jul  8 2019, 14:54:52)
[Clang 6.0 (clang-600.0.57)] on darwin
Type "help", "copyright", "credits" or "license" for more information.
(InteractiveConsole)
>>> import boto
>>> boto.__version__
'2.49.0'
```

### installing

You can install shiv by simply downloading a release from https://github.com/linkedin/shiv/releases or via `pip` / `pypi`:

```sh
pip install shiv
```

You can even create a pyz _of_ shiv _using_ shiv!

```sh
python3 -m venv .
source bin/activate
pip install shiv
shiv -c shiv -o shiv shiv
```

### developing

We'd love contributions! Getting bootstrapped to develop is easy:

```sh
git clone git@github.com:linkedin/shiv.git
cd shiv
python3 -m venv venv
source ./venv/bin/activate
python3 -m pip install --upgrade build
python3 -m build
python3 -m pip install -e .
```

Don't forget to run and write tests:

```sh
python3 -m pip install tox
tox
```

To build documentation when you changed something in `docs`:

```sh
python3 -m pip install -r docs/requirements.txt
sphinx-build docs build/html
```

### gotchas

Zipapps created with shiv are not guaranteed to be cross-compatible with other architectures. For example, a `pyz`
 file built on a Mac may only work on other Macs, likewise for RHEL, etc. This usually only applies to zipapps that have C extensions in their dependencies. If all your dependencies are pure python, then chances are the `pyz` _will_ work on other platforms. Just something to be aware of.

Zipapps created with shiv *will* extract themselves into `~/.shiv`, unless overridden via
`SHIV_ROOT`. If you create many utilities with shiv, you may want to occasionally clean this
directory.

---

### acknowledgements

Similar projects:

* [PEX](https://github.com/pantsbuild/pex)
* [pyzzer](https://pypi.org/project/pyzzer/#description)
* [superzippy](https://github.com/brownhead/superzippy)

Logo by Juliette Carvalho
