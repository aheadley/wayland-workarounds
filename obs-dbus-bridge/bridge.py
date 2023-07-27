#!/usr/bin/env python

from dataclasses import dataclass
import json
import logging
import multiprocessing
import os.path
import subprocess
import sys
from typing import Callable

try:
    import obspython as libobs # pyright: ignore
except ImportError:
    libobs = None

REQUIREMENTS = """
dbus-python==1.3.2
PyGObject==3.44.1
""".strip()
_deps_install_attempted = False
while True:
    try:
        import dbus
        import dbus.service
        import dbus.mainloop.glib
        import obsws_python as obsws
        from gi.repository import GLib
    except ImportError as err:
        if libobs is not None and not _deps_install_attempted:
            # VENV_PATH = os.path.join(..., ".dbus-bridge-venv")
            VENV_PATH = "/home/aheadley/tmp/obs-scripting-test/test-env"
            if not os.path.exists(VENV_PATH):
                # create venv
                ret = subprocess.call([sys.executable, "-m", "venv",
                                       "--upgrade-deps", VENV_PATH])

            VENV_PIP_PATH = os.path.join(VENV_PATH, "bin", "pip")
            pip_freeze = subprocess.check_output([VENV_PIP_PATH, "freeze"]).decode().strip()

            for req in REQUIREMENTS.strip().split("\n"):
                if req not in pip_freeze:
                    ret = subprocess.call([VENV_PIP_PATH, "install", "-U", req])
                    # if ret != 0:
                    #     raise Exception("Failed to install requirements")

            # fix up sys.path
            VENV_PYTHON_PATH = os.path.join(VENV_PATH, "bin", "python")
            path_json_str = subprocess.check_output([VENV_PYTHON_PATH, "-c",
                "import json, sys; print(json.dumps(sys.path))"]).decode()
            for path in json.loads(path_json_str):
                if path not in sys.path:
                    sys.path.append(path)
            _deps_install_attempted = True
            continue
        else:
            raise err
    else:
        break

DBUS_NAMESPACE = "com.obsproject.Studio"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 4455

class ObsConnector(dbus.service.Object):
    def __init__(self, dbus_handle: dbus.SessionBus, object_path: str):
        dbus.service.Object.__init__(self, dbus_handle, object_path)
        self._object_path = object_path

def unwrap_response(resp):
    return {k: getattr(resp, k) for k in resp.attrs()}

class WebSocketConnector(ObsConnector):
    def __init__(self, bus_handle, object_path, **kwargs):
        super().__init__(bus_handle, object_path)
        self._obs = obsws.ReqClient(**kwargs)

    @dbus.service.method(DBUS_NAMESPACE, out_signature="a{sv}")
    def GetVersion(self) -> dict:
        return unwrap_response(self._obs.get_version())

    @dbus.service.method(DBUS_NAMESPACE, out_signature="as")
    def GetHotkeyList(self) -> list[str]:
        return self._obs.get_hotkey_list().hotkeys

    @dbus.service.method(DBUS_NAMESPACE, in_signature="s")
    def TriggerHotkeyByName(self, name: str):
        self._obs.trigger_hotkey_by_name(name)

    @dbus.service.method(DBUS_NAMESPACE, out_signature="as")
    def GetSceneList(self) -> list[str]:
        resp = self._obs.get_scene_list()
        return [s['sceneName'] for s in resp.scenes]

    @dbus.service.method(DBUS_NAMESPACE, out_signature="s")
    def GetCurrentProgramScene(self) -> str:
        return self._obs.get_current_program_scene().current_program_scene_name

    @dbus.service.method(DBUS_NAMESPACE, in_signature="s")
    def SetCurrentProgramScene(self, name: str):
        self._obs.set_current_program_scene(name)

    @dbus.service.method(DBUS_NAMESPACE, out_signature="s")
    def GetCurrentPreviewScene(self) -> str:
        return self._obs.get_current_preview_scene().current_preview_scene_name

    @dbus.service.method(DBUS_NAMESPACE, in_signature="s")
    def SetCurrentPreviewScene(self, name: str):
        self._obs.set_current_preview_scene(name)

    @dbus.service.method(DBUS_NAMESPACE, in_signature="b", out_signature="as")
    def GetInputKindList(self, unversioned: bool = False) -> list[str]:
        return self._obs.get_input_kind_list(unversioned).input_kinds

    @dbus.service.method(DBUS_NAMESPACE, out_signature="av")
    def GetInputList(self) -> list[dict]:
        return self._obs.get_input_list().inputs

    @dbus.service.method(DBUS_NAMESPACE, out_signature="a{sv}")
    def GetSpecialInputs(self) -> dict:
        resp = self._obs.get_special_inputs()
        return {k: getattr(resp, k) for k in resp.attrs() if getattr(resp, k) is not None}

    @dbus.service.method(DBUS_NAMESPACE, in_signature="s")
    def ToggleInputMute(self, inputName: str):
        self._obs.toggle_input_mute(inputName)

    @dbus.service.method(DBUS_NAMESPACE, out_signature="b")
    def GetVirtualCamStatus(self) -> bool:
        return self._obs.get_virtual_cam_status().output_active

    @dbus.service.method(DBUS_NAMESPACE, out_signature="b")
    def ToggleVirtualCam(self) -> bool:
        return self._obs.toggle_virtual_cam().output_active

    @dbus.service.method(DBUS_NAMESPACE)
    def StartVirtualCam(self):
        self._obs.start_virtual_cam()

    @dbus.service.method(DBUS_NAMESPACE)
    def StopVirtualCam(self):
        self._obs.stop_virtual_cam()

    @dbus.service.method(DBUS_NAMESPACE, out_signature="b")
    def GetReplayBufferStatus(self) -> bool:
        return self._obs.get_replay_buffer_status().output_active

    @dbus.service.method(DBUS_NAMESPACE, out_signature="b")
    def ToggleReplayBuffer(self) -> bool:
        return self._obs.toggle_replay_buffer().output_active

    @dbus.service.method(DBUS_NAMESPACE)
    def StartReplayBuffer(self):
        self._obs.start_replay_buffer()

    @dbus.service.method(DBUS_NAMESPACE)
    def StopReplayBuffer(self):
        self._obs.stop_replay_buffer()

    @dbus.service.method(DBUS_NAMESPACE)
    def SaveReplayBuffer(self):
        self._obs.save_replay_buffer()

    @dbus.service.method(DBUS_NAMESPACE, out_signature="s")
    def GetLastReplayBufferReplay(self):
        return self._obs.get_last_replay_buffer_replay().saved_replay_path

    @dbus.service.method(DBUS_NAMESPACE, out_signature="a{sv}")
    def GetStreamStatus(self):
        return unwrap_response(self._obs.get_stream_status())

    @dbus.service.method(DBUS_NAMESPACE, out_signature="b")
    def ToggleStream(self) -> bool:
        return self._obs.toggle_stream().output_active

    @dbus.service.method(DBUS_NAMESPACE)
    def StartStream(self):
        self._obs.start_stream()

    @dbus.service.method(DBUS_NAMESPACE)
    def StopStream(self):
        self._obs.stop_stream()

    @dbus.service.method(DBUS_NAMESPACE, out_signature="a{sv}")
    def GetRecordStatus(self) -> dict:
        return unwrap_response(self._obs.get_record_status())

    @dbus.service.method(DBUS_NAMESPACE)
    def ToggleRecord(self):
        self._obs.toggle_record()

    @dbus.service.method(DBUS_NAMESPACE)
    def StartRecord(self):
        self._obs.start_record()

    @dbus.service.method(DBUS_NAMESPACE, out_signature="s")
    def StopRecord(self) -> str:
        return self._obs.stop_record().output_path

    @dbus.service.method(DBUS_NAMESPACE)
    def ToggleRecordPause(self):
        self._obs.toggle_record_pause()

    @dbus.service.method(DBUS_NAMESPACE)
    def PauseRecord(self):
        self._obs.pause_record()

    @dbus.service.method(DBUS_NAMESPACE)
    def ResumeRecord(self):
        self._obs.resume_record()

    @dbus.service.method(DBUS_NAMESPACE, out_signature="b")
    def GetStudioModeEnabled(self) -> bool:
        return self._obs.get_studio_mode_enabled().studio_mode_enabled

    @dbus.service.method(DBUS_NAMESPACE, in_signature="b")
    def GetStudioModeEnabled(self, studio_mode_enabled: bool):
        return self._obs.set_studio_mode_enabled(studio_mode_enabled)

    @dbus.service.method(DBUS_NAMESPACE)
    def TriggerStudioModeTransition(self):
        self._obs.trigger_studio_mode_transition()

### OBS Script API ###
if libobs is not None:
    # global script state
    @dataclass
    class ScriptState:
        process: multiprocessing.Process
    SCRIPT_STATE: ScriptState = None

    # dbus_map = {"/": {
    #     "name": "root",
    #     "methods": [],
    #     "children": {
    #         "/Scenes": {
    #             "name": "scenes",
    #             "children": 'SceneObjectFactory',
    #         },
    #         "/Outputs": {
    #             "name": "outputs",
    #             "children": 'OutputObjectFactory',
    #         },
    #     },
    # }}

    # class DbusMeta(type):
    #     def __new__(cls, name, bases, attrs):
    #         return type.__new__(cls, name, bases, attrs)

    # class DbusObjectFactory(ObsConnector):
    #     object_fragment: str
    #     def __init__(self, dbus_handle: dbus.SessionBus):
    #         super().__init__(dbus_handle, self.object_fragment)

    #         # self.children =

    # class ScriptConnector(DbusObjectFactory):
    #     object_path = "/"

    #     def GetVersion():
    #         pass

    #     def TriggerHotkeyByName(name: str):
    #         pass

    #     class SceneCollection():
    #         object_path = "/Scenes"
    #         def GetSceneList():
    #             pass

    #         for scene in GetSceneList():
    #             class Scene():
    #                 object_path = f"/{scene}"

    #                 def MakeProgramScene():
    #                     pass

    def script_defaults(settings: dict) -> None:
        pass

    def script_description() -> str:
        return "Control OBS via D-Bus"

    def script_load(settings: dict) -> None:
        SCRIPT_STATE.process = multiprocessing.Process(target=proc_main)
        SCRIPT_STATE.process.start()

    def script_update(settings: dict) -> None:
        pass

    def script_unload() -> None:
        SCRIPT_STATE.process.terminate()
        SCRIPT_STATE.process.join()

    def script_save(settings: dict) -> None:
        pass

    def script_properties() -> dict:
        return {}

    def proc_main() -> None:
        # ds = DbusService(ScriptConnector)
        ds = DbusService(WebSocketConnector, {
            "host": DEFAULT_HOST, "port": DEFAULT_PORT,
            "password": "tHJt0OFieV2jAc4n"})
        ds.run()

    def script_main() -> None:
        globals()["SCRIPT_STATE"] = ScriptState()

### End OBS Script API ###

class DbusService:
    def __init__(self, connector: ObsConnector, connector_args: dict = {}):
        self._connector = lambda dbus_handle, object_path: \
            connector(dbus_handle, object_path, **connector_args)

    def run(self):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus_handle = dbus.SessionBus()
        name = dbus.service.BusName(DBUS_NAMESPACE, bus_handle)

        c = self._connector(bus_handle, "/")

        mainloop = GLib.MainLoop()
        mainloop.run()

def main(args: list[str]) -> None:
    ds = DbusService(WebSocketConnector, {
        "host": DEFAULT_HOST, "port": DEFAULT_PORT,
        "password": args[0]})
    ds.run()

if libobs is not None:
    # run as obs script
    script_main()

elif __name__ == "__main__":
    import sys

    main(sys.argv[1:])
