"""Import sibling packages both locally and on Databricks.

Tests import this repo as `src.adp`, so siblings are `src.bedoux` and `src.aglc`.
Databricks notebook tasks put `src/` itself on sys.path, so there they are plain
`bedoux` and `aglc`. Only pure-Python modules are imported through here.
"""

import importlib


def sibling(name):
    try:
        return importlib.import_module(f"src.{name}")
    except ImportError:
        return importlib.import_module(name)
