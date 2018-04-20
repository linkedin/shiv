import os
import sys
import zipfile

from contextlib import contextmanager


@contextmanager
def silence_stderr():
    with open(os.devnull, 'w') as devnull:
        stderr = sys.stderr
        sys.stderr = devnull
        yield
        sys.stderr = stderr


def current_zipfile():
    """A function to vend the current zipfile, if any"""
    if zipfile.is_zipfile(sys.argv[0]):
        fd = open(sys.argv[0], "rb")
        return zipfile.ZipFile(fd)


def loaded_from_zipfile(module):
    return hasattr(module.__spec__.loader, "archive")
