"""
This module contains the ``Environment`` object, which combines settings decided at build time with
overrides defined at runtime (via environment variables).
"""
import json
import os

from pathlib import Path


def str_bool(v):
    if not isinstance(v, bool):
        return str(v).lower() in ("yes", "true", "t", "1")
    return v


class Environment:
    INTERPRETER = "SHIV_INTERPRETER"
    ENTRY_POINT = "SHIV_ENTRY_POINT"
    MODULE = "SHIV_MODULE"
    ROOT = "SHIV_ROOT"
    FORCE_EXTRACT = "SHIV_FORCE_EXTRACT"
    COMPILE_PYC = "SHIV_COMPILE_PYC"
    COMPILE_WORKERS = "SHIV_COMPILE_WORKERS"
    EXTEND_PYTHONPATH = "SHIV_EXTEND_PYTHONPATH"

    def __init__(
        self,
        built_at,
        shiv_version,
        build_id=None,
        entry_point=None,
        script=None,
        always_write_cache=False,
        compile_pyc=True,
        extend_pythonpath=False,
    ):
        self.built_at = built_at
        self.shiv_version = shiv_version
        self.build_id = build_id
        self.always_write_cache = always_write_cache
        self.script = script

        # properties
        self._entry_point = entry_point
        self._compile_pyc = compile_pyc
        self._extend_pythonpath = extend_pythonpath

    @classmethod
    def from_json(cls, json_data):
        return Environment(**json.loads(json_data))

    def to_json(self):
        return json.dumps(
            # we strip the leading underscores to retain properties (such as _entry_point)
            {key.lstrip("_"): value for key, value in self.__dict__.items()}
        )

    @property
    def entry_point(self):
        return os.environ.get(self.ENTRY_POINT, os.environ.get(self.MODULE, self._entry_point))

    @property
    def interpreter(self):
        return os.environ.get(self.INTERPRETER, None)

    @property
    def root(self):
        root = os.environ.get(self.ROOT)
        return Path(root) if root is not None else None

    @property
    def force_extract(self):
        return str_bool(os.environ.get(self.FORCE_EXTRACT, self.always_write_cache))

    @property
    def compile_pyc(self):
        return str_bool(os.environ.get(self.COMPILE_PYC, self._compile_pyc))

    @property
    def extend_pythonpath(self):
        return str_bool(os.environ.get(self.EXTEND_PYTHONPATH, self._extend_pythonpath))

    @property
    def compile_workers(self):
        try:
            return int(os.environ.get(self.COMPILE_WORKERS, 0))
        except ValueError:
            return 0
