#!/usr/bin/env python

import collections
import itertools
import logging
import os
import os.path
import time
import tomllib

import dbus
from libinput import LibInput, ContextType, EventType, DeviceCapability
from libinput.constant import ButtonState, KeyState
from libevdev._clib import Libevdev

APP_NAME = "global-shortcuts"

XDG_CONFIG_HOME = os.getenv("XDG_CONFIG_HOME") or "{HOME}/.config"
XDG_CONFIG_DIRS = os.getenv("XDG_CONFIG_DIRS") or "/etc/xdg"
XDG_CONFIG_DIRS = XDG_CONFIG_DIRS.split(":")

DEFAULT_SEAT = "seat0"
CONFIG_KEYS = ["keycodes", "actions", "devices"]
DEFAULT_KEYCODE_STATE = KeyState.PRESSED
DEFAULT_ACTION_TYPE = "DBUS"

EV_KEY = Libevdev._event_type_from_name("EV_KEY".encode())
VALID_EVENT_TYPES = [
    EventType.KEYBOARD_KEY,
    EventType.POINTER_BUTTON,
]

SimpleEvent = collections.namedtuple('SimpleEvent', [
    "name",
    "keycode",
    "state",
    "action",
    "device",
])
# ComboEvent = collections.namedtuple('ComboEvent')

def config_merge(base, next):
    result = {}
    for config_key in CONFIG_KEYS:
        result[config_key] = base[config_key].copy()
        for key_group in next[config_key]:
            if key_group in base[config_key]:
                result[config_key][key_group] += next[config_key][key_group]
            else:
                result[config_key][key_group] = next[config_key][key_group]
    return result

def load_config(config_filename=None):
    CONFIG_FILE_PATHS = [os.path.join(p, APP_NAME) for p in [XDG_CONFIG_HOME] + XDG_CONFIG_DIRS]
    if config_filename is None:
        config_filename = os.path.join(XDG_CONFIG_HOME, APP_NAME)
    config_filenames = [config_filename] + CONFIG_FILE_PATHS

    config = {
        "keycodes": {},
        "actions": {},
        "devices": {},
    }

    for cf in config_filenames[::-1]:
        try:
            with open(cf, "rb") as h:
                config_data = tomllib.load(h)
            config = config_merge(config, config_data)
        except Exception as e:
            print(e)

    return config

def get_dbus_handle():
    return dbus.SessionBus()

def get_input_handle():
    libinput_handle = LibInput(context_type=ContextType.UDEV)
    libinput_handle.assign_seat(DEFAULT_SEAT)
    return libinput_handle

def get_bindings(config):
    binding_names = set(config[CONFIG_KEYS[0]].keys())
    for k in CONFIG_KEYS:
        binding_names = binding_names.intersection(set(config[k].keys()))
    binding_names = list(binding_names)

    bindings = []
    for binding_name in binding_names:
        for event_product in itertools.product(config["keycodes"][binding_name],
                                   config["actions"][binding_name],
                                   config["devices"][binding_name]):
            state = event_product[0].split(':')
            keycode = get_keycode_from_key_name(state[0].upper())
            device = DeviceCapability[event_product[2].upper()]
            if len(state) > 1:
                state = state[1]
                if device == DeviceCapability.POINTER:
                    state = ButtonState[state.upper()]
                elif device == DeviceCapability.KEYBOARD:
                    state = KeyState[state.upper()]
                else:
                    raise Exception('invalid state:{}'.format(state))
            else:
                if device == DeviceCapability.POINTER:
                    state = ButtonState.PRESSED
                else:
                    state = DEFAULT_KEYCODE_STATE
            binding = SimpleEvent(name=binding_name, keycode=keycode, state=state, action=event_product[1], device=device)
            bindings.extend([
                binding
            ])
            print(binding)
    return bindings

def get_key_name_from_keycode(keycode):
    return Libevdev._event_code_get_name(EV_KEY, keycode).decode()

def get_keycode_from_key_name(key_name):
    return Libevdev._event_code_from_name(EV_KEY, key_name.encode())

def filter(binding, event):
    if binding.device in event.device.capabilities:
        if event.type is EventType.POINTER_BUTTON:
            if event.button == binding.keycode \
                    and event.button_state == binding.state:
                return binding
        elif event.type is EventType.KEYBOARD_KEY:
            if event.key == binding.keycode \
                    and event.key_state == binding.state:
                return binding
    return None

def check_filter(bindings, event):
    return (r for r in map(lambda b: filter(b, event), bindings) if r is not None)

def run_action(dbus_handle, binding):
    print(binding.action)
    action = binding.action.split(":")
    if len(action) > 1:
        action_type = action[0].upper()
        action = action[1]
    else:
        action_type = DEFAULT_ACTION_TYPE
        action = action[0]

    if action_type == "DBUS":
        parts = action.split("/")
        ns = parts[0]
        func = parts[-1]
        path = action.removeprefix(ns).removesuffix(func) #.rstrip("/")
        print("dbus ns={} path={} func={}".format(ns, path, func))
        try:
            f = dbus_handle.get_object(ns, path).get_dbus_method(func)
            try:
                f()
            except dbus.exceptions.DBusException as call_err:
                print("call_err")
        except dbus.exceptions.DBusException as name_err:
            print("name_err")


def run_loop(bindings, input_handle, dbus_handle):
    # fake_select_nb = lambda h: h.next_event_type() and next(h.events)

    keep_running = True
    while keep_running:
        # ev = fake_select_nb(input_handle)
        # if ev is not None:
        for ev in input_handle.events:
            try:
                if ev.type in VALID_EVENT_TYPES:
                    if ev.type == EventType.POINTER_BUTTON:
                        print("ev: keycode={} key_name={} state={} device={}".format(
                            ev.button,
                            get_key_name_from_keycode(ev.button),
                            ev.button_state,
                            ev.device.capabilities
                        ))
                    elif ev.type == EventType.KEYBOARD_KEY:
                        print("ev: keycode={} key_name={} state={} device={}".format(
                            ev.key,
                            get_key_name_from_keycode(ev.key),
                            ev.key_state,
                            ev.device.capabilities
                        ))
            except AttributeError:
                pass
            for activated_binding in check_filter(bindings, ev):
                run_action(dbus_handle, activated_binding)
        time.sleep(0.01)

def main(args):
    if len(args) > 1:
        running_config = load_config(args[1])
    else:
        running_config = load_config()
    dbus_handle = get_dbus_handle()
    input_handle = get_input_handle()
    bindings = get_bindings(running_config)
    try:
        run_loop(bindings, input_handle, dbus_handle)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    import sys

    main(sys.argv)
