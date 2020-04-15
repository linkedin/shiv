"""A simple low-feature cross-platform file lock implementation.

Code is based on github.com/benediktschmitt/py-filelock
"""

import os
import time

try:
    import msvcrt  # type: ignore
except ImportError:
    msvcrt = None  # type: ignore

try:
    import fcntl  # type: ignore
except ImportError:
    fcntl = None  # type: ignore

OPEN_MODE = os.O_RDWR | os.O_CREAT | os.O_TRUNC


def acquire_win(lock_file):  # pragma: no cover
    """Acquire a lock file on windows."""
    try:
        fd = os.open(lock_file, OPEN_MODE)
    except OSError:
        pass
    else:
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        except (IOError, OSError):
            os.close(fd)
        else:
            return fd


def acquire_nix(lock_file):  # pragma: no cover
    """Acquire a lock file on linux or osx."""
    fd = os.open(lock_file, OPEN_MODE)

    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (IOError, OSError):
        os.close(fd)
    else:
        return fd


class FileLock:
    """A rudimentary file lock class."""

    def __init__(self, lock_file):
        # The path to the lock file.
        self.lock_file = lock_file

        # The file descriptor for the lock file
        self.lock_file_fd = None

    @property
    def is_locked(self):
        """This property signals if we are holding the lock."""
        return self.lock_file_fd is not None

    def __enter__(self, poll_intervall=0.01):

        while not self.is_locked:

            if msvcrt:
                self.lock_file_fd = acquire_win(self.lock_file)
            elif fcntl:
                self.lock_file_fd = acquire_nix(self.lock_file)

            time.sleep(poll_intervall)

        return self

    def __exit__(self, exc_type, exc_value, traceback):

        if self.is_locked:

            fd = self.lock_file_fd
            self.lock_file_fd = None

            if msvcrt:
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            elif fcntl:
                fcntl.flock(fd, fcntl.LOCK_UN)

            os.close(fd)
