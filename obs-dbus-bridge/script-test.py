#!/usr/bin/env python

import os
import pprint
import sys

try:
    import obspython as libobs # pyright: ignore
except ImportError:
    libobs = None

OUTPUT_DIR = "/home/aheadley/tmp/obs-scripting-test"

def dump_env(name, **kwargs):
    with open(f"{OUTPUT_DIR}/{name}.txt", "w") as f:
        f.write(f"kwargs = {pprint.pformat(kwargs)}\n")
        f.write(f"environ = {pprint.pformat(os.environ)}\n")

        site = {
            "exec_prefix": sys.exec_prefix,
            "executable": sys.executable,
            "prefix": sys.prefix,
            "version": sys.version,
            "path": sys.path,
        }
        f.write(f"site = {pprint.pformat(site)}\n")
        f.write(f"libobs = {pprint.pformat(libobs)}\n")

def script_defaults(settings: dict) -> None:
    dump_env("script_defaults", settings=settings)

def script_description() -> str:
    return "this is the script_description() output"

def script_load(settings: dict) -> None:
    dump_env("script_load", settings=settings)

def script_update(settings: dict) -> None:
    dump_env("script_update", settings=settings)

def script_unload() -> None:
    dump_env("script_unload")

def script_save(settings: dict) -> None:
    dump_env("script_save", settings=settings)

# def script_properties() -> dict:
#     return {}

def script_main() -> None:
    pass
