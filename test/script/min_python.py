# /// script
# requires-python = ">=3.8"
# ///

# No external dependencies

import json

document = {
    "hello": "world",
    "foo": {
        "bar": 1,
        "baz": 2,
    },
}

print(json.dumps(document))
