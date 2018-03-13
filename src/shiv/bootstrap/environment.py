import copy
import json
import os

from pathlib import Path


class Environment:
    INTERPRETER = 'SHIV_INTERPRETER'
    ENTRY_POINT = 'SHIV_ENTRY_POINT'
    SITE_PACKAGES = 'SHIV_SITE_PACKAGES'
    FORCE_EXTRACT = 'SHIV_FORCE_EXTRACT'
    ZIP_SAFE = 'SHIV_ZIP_SAFE'

    def __init__(
        self,
        build_id=None,
        entry_point=None,
        shared_object_map=None,
        zip_safe=False,
        always_write_cache=False,
    ):
        self.build_id = build_id
        self.shared_object_map = shared_object_map
        self.always_write_cache = always_write_cache

        # properties
        self._entry_point = entry_point
        self._zip_safe = zip_safe

    @classmethod
    def from_json(cls, json_data):
        return Environment(**json.loads(json_data))

    def to_json(self):
        d = copy.copy(self.__dict__)
        del d['_entry_point']
        del d['_zip_safe']
        d['entry_point'] = self.entry_point
        d['zip_safe'] = self.zip_safe
        return json.dumps(d)

    @property
    def entry_point(self):
        return os.environ.get(self.ENTRY_POINT, self._entry_point)

    @property
    def zip_safe(self):
        return os.environ.get(self.ZIP_SAFE, self._entry_point)

    @property
    def interpreter(self):
        return os.environ.get(self.INTERPRETER, None)

    @property
    def site_packages(self):
        sp = os.environ.get(self.SITE_PACKAGES)
        return Path(sp) if sp is not None else None

    @property
    def force_extract(self):
        return bool(os.environ.get(self.FORCE_EXTRACT, self.always_write_cache))
