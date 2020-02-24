import logging
import os

import xbmc

from lib.daemon import Daemon
from lib.kodi import ADDON_PATH, ADDON_DATA, get_int_setting, set_logger
from lib.os_platform import PLATFORM


def get_platform_arch():
    return "{}_{}".format(PLATFORM.system.value, PLATFORM.arch.value)


def get_port():
    return get_int_setting("port")


class DaemonMonitor(xbmc.Monitor):
    def __init__(self):
        super(DaemonMonitor, self).__init__()
        self._daemon = Daemon("torrest", os.path.join(ADDON_PATH, "resources", "bin", get_platform_arch()))
        self._port = get_port()
        self._settings = os.path.join(ADDON_DATA, "settings.json")

    def start(self):
        self._daemon.start(port=self._port, settings=self._settings, level=logging.INFO)

    def stop(self):
        self._daemon.stop()

    def onSettingsChanged(self):
        port = get_port()
        if port != self._port:
            self._port = port
            self.stop()
            self.start()


def run():
    set_logger(level=logging.INFO)
    monitor = DaemonMonitor()
    monitor.start()
    monitor.waitForAbort()
    monitor.stop()
