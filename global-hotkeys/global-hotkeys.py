#!/usr/bin/env python

import collections
import itertools
import logging
import os
import os.path
import pwd
import subprocess
import time
import tomllib
from collections.abc import Iterable, Sequence, Collection, Callable
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Tuple

import dbus
from libinput import LibInput, ContextType, EventType, DeviceCapability
from libinput.constant import ButtonState, KeyState
from libinput.event import Event as LibInputEvent, KeyboardEvent, PointerEvent
from libinput.device import Device as LibInputDevice
from libevdev._clib import Libevdev
import threading
import argparse

APP_NAME = "global-hotkeys"

ENV_HOME = os.getenv("HOME") or pwd.getpwuid(os.geteuid()).pw_dir
XDG_CONFIG_HOME = os.getenv("XDG_CONFIG_HOME") or os.path.join(ENV_HOME, ".config")

EV_KEY: int = Libevdev._event_type_from_name("EV_KEY".encode())
VALID_EVENT_TYPES: tuple[EventType] = (
    EventType.KEYBOARD_KEY,
    EventType.POINTER_BUTTON,
)

class ActionType(Enum):
    DBUS = auto()
    EXEC = auto()

DEFAULT_CONFIG_FILENAME = "config.toml"
DEFAULT_CONFIG_PATH = os.path.join(XDG_CONFIG_HOME, APP_NAME, DEFAULT_CONFIG_FILENAME)
DEFAULT_SEAT = "seat0"
DEFAULT_KEYCODE_STATE = "PRESSED"
DEFAULT_ACTION_TYPE = ActionType.DBUS

ACTION_TYPE_SEP: str = ":"
DBUS_PATH_SEP: str = "/"

InputEvent = KeyboardEvent|PointerEvent
InputState = KeyState|ButtonState

LOG = logging.getLogger(APP_NAME)

def key_name_from_code(keycode: int) -> str:
    return Libevdev._event_code_get_name(EV_KEY, keycode).decode()

def keycode_from_name(key_name: str) -> int:
    return Libevdev._event_code_from_name(EV_KEY, key_name.encode())

@dataclass
class SimpleBinding:
    name: str
    keycodes: Tuple[int]
    state: KeyState|ButtonState
    action: Callable
    device: LibInputDevice|None

    def matches(self, event: InputEvent, held_keys: set[int]) -> bool:
        if self.device is None or self.device == event.device:
            if len(self.keycodes) > 1:
                if all(kc in held_keys for kc in self.keycodes):
                    return True
            else:
                if get_event_keycode(event) == self.keycodes[0] and get_event_state(event) == self.state:
                    return True

@dataclass
class BindingTriggeredEvent:
    timestamp: int
    source_event: LibInputEvent
    matched_binding: SimpleBinding

    def run(self, state: 'RunState'):
        LOG.info(f"Running {self.matched_binding.name}")
        self.matched_binding.action(state)

class ActionParser:
    @classmethod
    def parse(cls, action_str: str) -> Callable:
        action_str = action_str.strip()
        try:
            action_type_str, _ = action_str.split(ACTION_TYPE_SEP)
            try:
                action_type = ActionType[action_type_str.upper()]
                action_str = action_str[len(action_type_str) + len(ACTION_TYPE_SEP):]
            except KeyError:
                # either invalid action type or implicit default
                action_type = DEFAULT_ACTION_TYPE
                LOG.info(f"Defaulting to action type {action_type} for {action_str}")
        except ValueError:
            action_type = DEFAULT_ACTION_TYPE

        if action_type == ActionType.DBUS:
            return cls.build_dbus_action(action_str)
        elif action_type == ActionType.EXEC:
            return cls.build_exec_action(action_str)

    @classmethod
    def build_dbus_action(cls, action_str: str) -> Callable:
        parts = action_str.split(DBUS_PATH_SEP)
        namespace = parts[0]
        method = parts[-1]
        path = action_str.removeprefix(namespace).removesuffix(method)

        def dbus_action(state: 'RunState') -> None:
            try:
                object = state.dbus_session_handle.get_object(namespace, path)
                object_method = object.get_dbus_method(method)
                try:
                    object_method()
                except dbus.exceptions.DBusException as call_err:
                    LOG.warning(f"Error calling {action_str}: {call_err}")
            except dbus.exceptions.DBusException as object_err:
                LOG.warning(f"Error getting object {action_str}: {object_err}")

        return dbus_action

    @classmethod
    def build_exec_action(cls, action_str: str) -> Callable:
        def exec_action(state: 'RunState') -> None:
            try:
                ret = subprocess.call(action_str, shell=True,
                    timeout=(state.config["general"]["exec-timeout"] / 1000),
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL)
                LOG.debug(f"Executed {action_str} with return code {ret}")
            except subprocess.TimeoutExpired as err:
                LOG.warning(f"Timeout executing {action_str}: {err}")
            except OSError as err:
                LOG.warning(f"Error executing {action_str}: {err}")
        return exec_action

class ConfigManager:
    def __init__(self, config_filename=DEFAULT_CONFIG_PATH):
        self._config: dict[str, dict] = {}
        self._config_filename = config_filename
        self.load()

    def __getitem__(self, key: str):
        return self._config[key]

    def _parse_keycode(self, keycode_str: str) -> Tuple[str, InputState]:
        try:
            key_name, state = keycode_str.split(":", 1)
            state = state.upper()
        except ValueError:
            key_name = keycode_str
            state = DEFAULT_KEYCODE_STATE
        if key_name.startswith("KEY_"):
            state_typed = KeyState[state]
        elif key_name.startswith("BTN_"):
            state_typed = ButtonState[state]
        else:
            raise ValueError(f"Unknown type for key state: {state}")

        return key_name, state_typed

    def load(self):
        with open(self._config_filename, "rb") as config_handle:
            self._config = tomllib.load(config_handle)

    def generate_bindings(self, active_devices: dict[str, LibInputDevice] = None):
        if active_devices is None:
            active_devices = {}
        for binding_name, binding_data in self._config["bindings"].items():
            binding_name: str
            binding_data: dict[str, Any]

            actions = [
                ActionParser.parse(action) for action in binding_data["actions"]
            ]
            try:
                devices = binding_data["devices"]
                # TODO: filter devices from active_devices
            except KeyError:
                devices = [None]
            for device in devices:
                if "keycodes" in binding_data:
                    for keycode_str in binding_data["keycodes"]:
                        key_name, key_state = self._parse_keycode(keycode_str)
                        keycode = keycode_from_name(key_name)
                        for action in actions:
                            binding = SimpleBinding(
                                name=binding_name,
                                keycodes=(keycode,),
                                state=key_state,
                                action=action,
                                device=device,
                            )
                            LOG.debug(f"Generated binding: {binding}")
                            yield binding
                if "keycode-combos" in binding_data:
                    for combo_set in binding_data["keycode-combos"]:
                        keycodes = tuple(keycode_from_name(self._parse_keycode(keycode)[0]) \
                                        for keycode in combo_set)
                        for action in actions:
                            binding = SimpleBinding(
                                name=binding_name,
                                keycodes=keycodes,
                                state=KeyState[DEFAULT_KEYCODE_STATE],
                                action=action,
                                device=device,
                            )
                            LOG.debug(f"Generated combo binding: {binding}")
                            yield binding

def get_event_state(ev: InputEvent) -> InputState:
    try:
        return ev.key_state
    except AttributeError:
        return ev.button_state

def get_event_keycode(ev: InputEvent) -> int:
    try:
        return ev.key
    except AttributeError:
        return ev.button

@dataclass
class RunState:
    dbus_session_handle: dbus.SessionBus
    libinput_handle: LibInput
    config: ConfigManager

class EventManager:
    def __init__(self):
        self._held_keys: dict[int, bool] = {}

    def _mark_held(self, ev: InputEvent):
        if get_event_state(ev):
            self._held_keys[get_event_keycode(ev)] = True
        else:
            self._held_keys[get_event_keycode(ev)] = False

    @property
    def held_keys(self) -> set[int]:
        return set(filter(lambda kc: self._held_keys[kc], self._held_keys.keys()))

    def run_once(self, event_stream, state: RunState, bindings: list[SimpleBinding]):
        ev = next(event_stream)
        if ev.type in VALID_EVENT_TYPES:
            LOG.debug(f"Received event: {ev}")
            self._mark_held(ev)
            held_keys = self.held_keys
            for binding in bindings:
                if binding.matches(ev, held_keys):
                    tev = BindingTriggeredEvent(time.time(), ev, binding)
                    tev.run(state)

    def run_forever(self, state: RunState, bindings: list[SimpleBinding] = None):
        if bindings is None:
            bindings = list(state.config.generate_bindings())
            LOG.info(f"Using implicitly generated bindings: {len(bindings)}")

        event_stream = state.libinput_handle.events

        while True:
            try:
                self.run_once(event_stream, state, bindings)
            except KeyboardInterrupt:
                break
            time.sleep(0.01)

def get_dbus_handle() -> dbus.SessionBus:
    return dbus.SessionBus()

def get_input_handle() -> LibInput:
    libinput_handle = LibInput(context_type=ContextType.UDEV)
    libinput_handle.assign_seat(DEFAULT_SEAT)
    return libinput_handle


def main(args: list[str]):
    parser = argparse.ArgumentParser(description="Global hotkeys")

    parser.add_argument('--config', default=DEFAULT_CONFIG_PATH)

    opts = parser.parse_args(args)

    state = RunState(get_dbus_handle(),
                     get_input_handle(),
                     ConfigManager(opts.config))
    evm = EventManager()
    evm.run_forever(state)

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG)
    main(sys.argv[1:])
