from pathlib import Path

import pytest

from shiv.inline_script import parse_script_metadata


class TestInlineScript:
    @pytest.mark.parametrize(
        "script_location,expected_metadata",
        [
            ("test/script/deps.py", {
                "script": {
                    "dependencies": [
                        "pyyaml<7",
                        "rich"
                    ],
                }
            }),
            ("test/script/min_python.py", {
                "script": {
                    "requires-python": ">=3.8",
                }
            }),
            ("test/script/deps_and_python.py", {
                "script": {
                    "requires-python": ">=3.8",
                    "dependencies": [
                        "python-dateutil",
                        "rich",
                    ],
                }
            }),
            ("test/package/hello/__init__.py", {}),
        ],
    )
    def test_parse_script_metadata(self, script_location, expected_metadata):
        script_text = Path(script_location).read_text()
        assert parse_script_metadata(script_text) == expected_metadata
