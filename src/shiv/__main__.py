"""
Shim for package execution (python3 -m shiv ...).
"""
from .commands import shiv

if __name__ == "__main__":  # pragma: no cover
    shiv()
