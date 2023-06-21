#!/usr/bin/env python

import dbus

try:
    import obspython as libobs
except ImportError:
    libobs = None

class DbusService:
    pass

class ObsConnector:
    pass

class WebsocketConnector(ObsConnector):
    pass

class ScriptConnector(ObsConnector):
    pass

### OBS Script API ###

# global script state
SCRIPT_STATE = {}

def script_defaults(settings: dict) -> None:
    pass

def script_description() -> str:
    return "FIXME"

def script_load(settings: dict) -> None:
    pass

def script_update(settings: dict) -> None:
    pass

def script_unload() -> None:
    pass

def script_save(settings: dict) -> None:
    pass

def script_properties() -> dict:
    return {}

### End OBS Script API ###

def run_as_main(args: list[str]) -> None:
    pass

if __name__ == "__main__":
    import sys

    run_as_main(sys.argv)
