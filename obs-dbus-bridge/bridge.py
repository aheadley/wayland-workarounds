#!/usr/bin/env python

import dbus
import dbus.service
import dbus.mainloop.glib
import obsws_python as obsws
from gi.repository import GLib

DBUS_NAMESPACE = "com.obsproject.Studio"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 4455

try:
    import obspython as libobs
except ImportError:
    libobs = None

class DbusService:
    pass

class ObsConnector:
    pass

class WebSocketConnector(ObsConnector):
    pass

class ScriptConnector(ObsConnector):
    pass

def unwrap_response(resp):
    return {k: getattr(resp, k) for k in resp.attrs()}

class WebSocketApi(dbus.service.Object):
    def __init__(self, bus_handle, object_path, obs: obsws.ReqClient):
        dbus.service.Object.__init__(self, bus_handle, object_path)
        self._obs = obs

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

def main(args: list[str]) -> None:
    obs = obsws.ReqClient(host=DEFAULT_HOST, port=DEFAULT_PORT, password=args[0])

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus_handle = dbus.SessionBus()
    name = dbus.service.BusName(DBUS_NAMESPACE, bus_handle)
    wsapi = WebSocketApi(bus_handle, '/WebSocketApi', obs)

    mainloop = GLib.MainLoop()
    mainloop.run()

if libobs is not None:
    # run as obs script
    pass
elif __name__ == "__main__":
    import sys

    main(sys.argv[1:])
