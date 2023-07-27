#!/usr/bin/env python

import dbus
import dbus.service
import dbus.mainloop.glib
import obsws_python as obsws
from gi.repository import GLib

DBUS_NAMESPACE = "com.obsproject.Studio"

obs = obsws.ReqClient(host="127.0.0.1", port=4455, password="tHJt0OFieV2jAc4n", timeout=3)

# resp = obs.get_version()
# print(resp)

# class WebSocketApi(dbus.service.Object):
#     def __init__(self, bus_handle, object_path):
#         dbus.service.Object.__init__(self, bus_handle, object_path)

#     @dbus.service.method(DBUS_NAMESPACE, in_signature="", out_signature="s")
#     def GetVersion(self):
#         version = f"0.1 / {obs.get_version().obs_version}"
#         print(f"GetVersion={version}")
#         return version

#     @dbus.service.method(DBUS_NAMESPACE,
#                          in_signature='', out_signature='')
#     def Exit(self):
#         mainloop.quit()

# dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
# bus_handle = dbus.SessionBus()
# name = dbus.service.BusName(DBUS_NAMESPACE, bus_handle)
# wsapi = WebSocketApi(bus_handle, '/WebSocketApi')

# mainloop = GLib.MainLoop()
# mainloop.run()
