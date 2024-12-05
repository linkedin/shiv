# /// script
# dependencies = [
#   "pyyaml<7",
#   "rich",
# ]
# ///

import yaml
from rich.pretty import pprint

document = """
  hello: world
  foo:
    bar: 1
    baz: 2
"""
pprint(yaml.safe_load(document))
