"""
This module contains the ``Environment`` object, which combines settings decided at build time with
overrides defined at runtime (via environment variables).
"""
import copy
import json
import os

from pathlib import Path


class Environment:
    INTERPRETER = "SHIV_INTERPRETER"
    ENTRY_POINT = "SHIV_ENTRY_POINT"
    MODULE = "SHIV_MODULE"
    ROOT = "SHIV_ROOT"
    FORCE_EXTRACT = "SHIV_FORCE_EXTRACT"

    def __init__(
        self,
        build_id=None,
        entry_point=None,
        always_write_cache=False,
    ):
        self.build_id = build_id
        self.always_write_cache = always_write_cache

        # properties
        self._entry_point = entry_point

    @classmethod
    def from_json(cls, json_data):
        return Environment(**json.loads(json_data))

    def to_json(self):
        d = copy.copy(self.__dict__)
        del d["_entry_point"]
        d["entry_point"] = self.entry_point
        return json.dumps(d)

    @property
    def entry_point(self):
        return os.environ.get(
            self.ENTRY_POINT,
            os.environ.get(self.MODULE, self._entry_point),
        )

    @property
    def interpreter(self):
        return os.environ.get(self.INTERPRETER, None)

    @property
    def root(self):
        root = os.environ.get(self.ROOT)
        return Path(root) if root is not None else None

    @property
    def force_extract(self):
        return bool(os.environ.get(self.FORCE_EXTRACT, self.always_write_cache))
