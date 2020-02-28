import logging
import os
import time

import requests
import xbmc
import xbmcgui

from lib import kodi
from lib.daemon import Daemon
from lib.os_platform import get_platform_arch


class DaemonTimeoutError(Exception):
    pass


class DaemonMonitor(xbmc.Monitor):
    _settings_prefix = "s"
    _settings_separator = ":"
    _settings_get_uri = "settings/get"
    _settings_set_uri = "settings/set"

    def __init__(self):
        super(DaemonMonitor, self).__init__()
        self._daemon = Daemon("torrest", os.path.join(kodi.ADDON_PATH, "resources", "bin", get_platform_arch()))
        self._port = self.get_port()
        self._settings_path = os.path.join(kodi.ADDON_DATA, "settings.json")
        self._settings_spec = [s for s in kodi.get_all_settings_spec() if s["id"].startswith(
            self._settings_prefix + self._settings_separator)]

    @staticmethod
    def get_port():
        return kodi.get_int_setting("port")

    def start(self):
        self._daemon.start(port=self._port, settings=self._settings_path, level=logging.INFO)

    def stop(self):
        self._daemon.stop()

    def _request(self, method, url, **kwargs):
        return requests.request(method, "http://localhost:{}/{}".format(self._port, url), **kwargs)

    def wait(self, timeout=-1, notification=False):
        start = time.time()
        while timeout < 0 or time.time() - start <= timeout:
            try:
                self._request("get", "")
                if notification:
                    xbmcgui.Dialog().notification("Torrest", "Torrest daemon started", kodi.ADDON_ICON)
                return
            except requests.exceptions.ConnectionError:
                time.sleep(0.5)
        raise DaemonTimeoutError("Timeout reached")

    def get_kodi_settings(self):
        s = kodi.generate_dict_settings(self._settings_spec, separator=self._settings_separator)[self._settings_prefix]
        s["torrents_path"] = os.path.join(s["download_path"], "Torrents")
        return s

    def get_daemon_settings(self):
        r = self._request("get", self._settings_get_uri)
        if r.status_code != 200:
            logging.error("Failed getting daemon settings with code %d: %s", r.status_code, r.text)
            return None
        return r.json()

    def update_kodi_settings(self):
        daemon_settings = self.get_daemon_settings()
        if daemon_settings is None:
            return False
        kodi.set_settings_dict(daemon_settings, prefix=self._settings_prefix, separator=self._settings_separator)
        return True

    def update_daemon_settings(self):
        daemon_settings = self.get_daemon_settings()
        if daemon_settings is None:
            return False

        kodi_settings = self.get_kodi_settings()
        if daemon_settings != kodi_settings:
            logging.debug("Need to update daemon settings")
            r = self._request("post", self._settings_set_uri, json=kodi_settings)
            if r.status_code != 200:
                xbmcgui.Dialog().ok(kodi.translate(30102), r.json()["error"])
                return False

        return True

    def onSettingsChanged(self):
        port = self.get_port()
        if port != self._port:
            self._port = port
            self.stop()
            self.start()

        self.update_daemon_settings()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


def run():
    kodi.set_logger(level=logging.INFO)
    if not kodi.get_boolean_setting("migrated"):
        kodi.set_setting("migrated", "true")
        xbmcgui.Dialog().ok(kodi.translate(30100), kodi.translate(30101))
        kodi.open_settings()
    with DaemonMonitor() as monitor:
        monitor.wait(timeout=kodi.get_int_setting("timeout"), notification=True)
        monitor.update_kodi_settings()
        monitor.waitForAbort()
