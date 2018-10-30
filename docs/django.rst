Deploying django apps
---------------------

Because of how shiv works, you can ship entire django apps with shiv, even including the database if you want!

Defining an entrypoint
======================

First, we will need an entrypoint.

We'll call it ``main.py``, and store it at ``<project_name>/<project_name>/main.py`` (alongside ``wsgi.py``)

.. code-block:: python

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

*This is meant as an example. While it's fully production-ready, you might want to tweak it according to your project's needs.*


Build script
============

Next, we'll create a simple bash script that will build a zipapp for us.

Save it as ``build.sh`` (next to manage.py)

.. code-block:: sh

    #!/usr/bin/env bash

    # clean old build
    rm -r dist <project_name>.pyz

    # include the dependencies from `pip freeze`
    pip install -r <(pip freeze) --target dist/

    # or, if you're using pipenv
    # pip install -r  <(pipenv lock -r) --target dist/

    # specify which files to be included in the build
    # You probably want to specify what goes here
    cp -r \
    -t dist \
    <app1> <app2> manage.py db.sqlite3

    # finally, build!
    shiv --site-packages dist --compressed -p '/usr/bin/env python3' -o <project_name>.pyz -e <project_name>.main

And then, you can just do the following

.. code-block:: sh

    $ ./build.sh

    $ ./<project_name>.pyz

    # In production -

    $ ./<project_name>.pyz production
