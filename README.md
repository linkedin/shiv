[![PyPI](https://img.shields.io/pypi/v/shiv.svg)](https://pypi.python.org/pypi/shiv)
[![Build Status](https://travis-ci.org/linkedin/shiv.svg?branch=master)](https://travis-ci.org/linkedin/shiv)
[![AppVeyor Status](https://ci.appveyor.com/api/projects/status/vb9yht30n0iuy4y9?svg=true)](https://ci.appveyor.com/project/sixninetynine/shiv)
[![Coverage Status](https://coveralls.io/repos/github/linkedin/shiv/badge.svg)](https://coveralls.io/github/linkedin/shiv)
[![Documentation Status](https://readthedocs.org/projects/shiv/badge/?version=latest)](http://shiv.readthedocs.io/en/latest/?badge=latest)
[![License](https://img.shields.io/badge/License-BSD%202--Clause-orange.svg)](https://opensource.org/licenses/BSD-2-Clause)
[![Supported](https://img.shields.io/pypi/pyversions/shiv.svg)](https://pypi.python.org/pypi/shiv)

![snake](logo.png)

# shiv
shiv is a command line utility for building fully self-contained Python zipapps as outlined in [PEP 441](https://www.python.org/dev/peps/pep-0441/), but with all their dependencies included!

shiv's primary goal is making distributing Python applications fast & easy.

Full documentation can be found [here](http://shiv.readthedocs.io/en/latest/).

### sys requirements

- python3.6+
- linux/osx/windows

### how to

shiv has a few command line options of its own and accepts almost all options passable to `pip install`.

##### simple cli example

Creating an executable of pipenv with shiv:

```sh
$ shiv -c pipenv -o ~/bin/pipenv pipenv pew
$ ~/bin/pipenv --version
pipenv, version 2018.05.18
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

You can install shiv via `pip` / `pypi`

```sh
pip install shiv
```

You can even create a pyz _of_ shiv _using_ shiv!

```sh
python3 -m venv shiv
source shiv/bin/activate
pip install shiv
shiv -c shiv -o shiv shiv
```

### Django 

Because of how shiv works, you can ship entire django apps with shiv, even including the database if you want!

First, we need an entrypoint.

We'll call it `main.py`, and store it at `<project_name>/<project_name>/main.py` (alongside `wsgi.py`)

```python
import os
import sys

import django

# setup django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "<project_name>.settings")
django.setup()

try:
    production = sys.argv[1] == "production"
except IndexError:
    production = False

if production:
    import gunicorn.app.wsgiapp as wsgi

    # This is just a simple way to supply args to gunicorn
    sys.argv = [".", "<project_name>.wsgi", "--bind=0.0.0.0:80"]

    wsgi.run()
else:
    from django.core.management import call_command
    
    call_command("runserver")
```


Next, we'll create a simple bash script that will build a zipapp for us.

Save it as `build.sh` (next to `manage.py`)

```bash
#!/usr/bin/env bash

# clean old build
rm -r dist <project_name>.pyz

# include the dependencies
pip install -r <(pip freeze) --target dist/

# or, if you're using pipnev
# pip install -r  <(pipenv lock -r) --target dist/

# specify which files to be included in the build
cp -r \
-t dist \
<app1> <app2> manage.py db.sqlite3

# build!
shiv --site-packages dist --compressed -p '/usr/bin/env python3' -o <project_name>.pyz -e <project_name>.main
```

And then it's literally just

```
$ ./build.sh

$ ./<project_name>.pyz

or in production,

$ ./<project_name>.pyz production 
```




### developing

We'd love contributions! Getting bootstrapped to develop is easy:

```sh
git clone git@github.com:linkedin/shiv.git
cd shiv
python3 setup.py venv
. activate
python3 setup.py develop
```

Don't forget to run and write tests:

```sh
pip install tox
tox
```

### gotchas

Zipapps created with shiv are not cross-compatible with other architectures. For example, a `pyz`
 file built on a Mac will only work on other Macs, likewise for RHEL, etc.

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
