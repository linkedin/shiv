[![PyPI](https://img.shields.io/pypi/v/shiv.svg)](https://pypi.python.org/pypi/shiv)
[![Build Status](https://travis-ci.org/linkedin/shiv.svg?branch=master)](https://travis-ci.org/linkedin/shiv)
[![Documentation Status](https://readthedocs.org/projects/shiv/badge/?version=latest)](http://shiv.readthedocs.io/en/latest/?badge=latest)
[![License](https://img.shields.io/badge/License-BSD%202--Clause-orange.svg)](https://opensource.org/licenses/BSD-2-Clause)

# shiv 🔪
Shiv is a command line utility for building fully self contained Python zipapps as outlined in [PEP 441](http://legacy.python.org/dev/peps/pep-0441/), but with all their dependencies included.

While similar to tools like [pex](https://github.com/pantsbuild/pex), Shiv's primary goal is cli startup speed. A command line utility generated with Shiv will usually outperform one that was installed via `pip` thanks to the fact that Shiv completely avoids use of `pkg_resources` and the infamous [Issue 510](https://github.com/pypa/setuptools/issues/510).

### how to

Shiv has a few command line options of its own and accepts almost all options passable to `pip install`.

##### simple cli example

Creating an executable of aws-cli with shiv:

```sh
$ shiv -e awscli.clidriver:main -o aws awscli
$ ./aws --version
aws-cli/1.14.2 Python/3.6.1 Linux/3.10.0-514.21.2.el7.x86_64 botocore/1.8.6
```

##### complex example involving a wheel cache

Creating an interactive executable with a downloaded wheel of boto:

```sh
$ python3 -m pip download boto
Collecting boto
  File was already downloaded /tmp/tmp.iklsO1qyd3/boto-2.48.0-py2.py3-none-any.whl
Successfully downloaded boto
$ shiv -o boto.pyz --find-links . --no-index boto
 shiv! 🔪
Collecting boto
Installing collected packages: boto
Successfully installed boto-2.48.0
 done
$ ./boto.pyz
Python 3.6.1 (default, Apr 19 2017, 21:58:41)
[GCC 4.8.5 20150623 (Red Hat 4.8.5-4)] on linux
Type "help", "copyright", "credits" or "license" for more information.
(InteractiveConsole)
>>> import boto
>>>
```

### installing

You can install shiv via `pip`/`pypi`

```sh
pip install shiv
```

You can even create a pyz _of_ shiv _using_ shiv!

```sh
python3 -m venv shiv
source shiv/bin/activate
pip install shiv
shiv -e shiv.cli:main -o shiv shiv
```

### developing

Get bootstrapped

```sh
git clone git@gitli.corp.linkedin.com:loren/shiv.git
cd shiv
python3 setup.py venv
. activate
python3 setup.py develop
```

Run and write tests

```sh
pip install tox
tox
```
