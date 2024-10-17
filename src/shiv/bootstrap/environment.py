"""
This module contains the ``Environment`` object, which combines settings decided at build time with
overrides defined at runtime (via environment variables).
"""
import json
import os
from typing import Any, Dict, Optional


def str_bool(v) -> bool:
    if not isinstance(v, bool):
        return str(v).lower() in ("yes", "true", "t", "1")
    return v


class Environment:
    INTERPRETER: str = "SHIV_INTERPRETER"
    ENTRY_POINT: str = "SHIV_ENTRY_POINT"
    CONSOLE_SCRIPT: str = "SHIV_CONSOLE_SCRIPT"
    MODULE: str = "SHIV_MODULE"
    ROOT: str = "SHIV_ROOT"
    FORCE_EXTRACT: str = "SHIV_FORCE_EXTRACT"
    COMPILE_PYC: str = "SHIV_COMPILE_PYC"
    COMPILE_WORKERS: str = "SHIV_COMPILE_WORKERS"
    EXTEND_PYTHONPATH: str = "SHIV_EXTEND_PYTHONPATH"
    PREPEND_PYTHONPATH: str = "SHIV_PREPEND_PYTHONPATH"

    def __init__(
        self,
        built_at: str,
        shiv_version: str,
        always_write_cache: bool = False,
        build_id: Optional[str] = None,
        compile_pyc: bool = True,
        entry_point: Optional[str] = None,
        extend_pythonpath: bool = False,
        prepend_pythonpath: Optional[str] = None,
        hashes: Optional[Dict[str, Any]] = None,
        no_modify: bool = False,
        reproducible: bool = False,
        script: Optional[str] = None,
        preamble: Optional[str] = None,
        root: Optional[str] = None,
    ) -> None:
        self.shiv_version: str = shiv_version
        self.always_write_cache: bool = always_write_cache
        self.build_id: Optional[str] = build_id
        self.built_at: str = built_at
        self.hashes: Optional[Dict[str, Any]] = hashes or {}
        self.no_modify: bool = no_modify
        self.reproducible: bool = reproducible
        self.preamble: Optional[str] = preamble

        # properties
        self._entry_point: Optional[str] = entry_point
        self._compile_pyc: bool = compile_pyc
        self._extend_pythonpath: bool = extend_pythonpath
        self._prepend_pythonpath: Optional[str] = prepend_pythonpath
        self._root: Optional[str] = root
        self._script: Optional[str] = script

    @classmethod
    def from_json(cls, json_data) -> "Environment":
        return Environment(**json.loads(json_data))

    def to_json(self) -> str:
        return json.dumps(
            # we strip the leading underscores to retain properties (such as _entry_point)
            {key.lstrip("_"): value for key, value in self.__dict__.items()}
        )

    @property
    def entry_point(self) -> Optional[str]:
        return os.environ.get(self.ENTRY_POINT, os.environ.get(self.MODULE, self._entry_point))

    @property
    def script(self) -> Optional[str]:
        return os.environ.get(self.CONSOLE_SCRIPT, self._script)

    @property
    def interpreter(self) -> Optional[str]:
        return os.environ.get(self.INTERPRETER, None)

    @property
    def root(self) -> Optional[str]:
        root = os.environ.get(self.ROOT, self._root)
        return root

    @property
    def force_extract(self) -> bool:
        return str_bool(os.environ.get(self.FORCE_EXTRACT, self.always_write_cache))

    @property
    def compile_pyc(self) -> bool:
        return str_bool(os.environ.get(self.COMPILE_PYC, self._compile_pyc))

    @property
    def extend_pythonpath(self) -> Optional[bool]:
        return str_bool(os.environ.get(self.EXTEND_PYTHONPATH, self._extend_pythonpath))

    @property
    def prepend_pythonpath(self) -> Optional[str]:
        """Prepend the given path to sys.path."""
        return os.environ.get(self.PREPEND_PYTHONPATH, self._prepend_pythonpath)

    @property
    def compile_workers(self) -> int:
        try:
            return int(os.environ.get(self.COMPILE_WORKERS, 0))
        except ValueError:
            return 0
