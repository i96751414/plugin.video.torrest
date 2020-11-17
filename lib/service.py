import logging
import os
import threading
import time

import requests
import xbmc
import xbmcgui

from lib import kodi
from lib.daemon import Daemon, DaemonNotFoundError
from lib.os_platform import get_platform_arch
from lib.settings import get_port, get_daemon_timeout, service_enabled, set_service_enabled


class AbortRequestedError(Exception):
    pass


class DaemonTimeoutError(Exception):
    pass


class DaemonMonitor(xbmc.Monitor):
    _settings_prefix = "s"
    _settings_separator = ":"
    _settings_get_uri = "settings/get"
    _settings_set_uri = "settings/set"

    def __init__(self):
        super(DaemonMonitor, self).__init__()
        self._lock = threading.Lock()
        self._daemon = Daemon(
            "torrest", os.path.join(kodi.ADDON_PATH, "resources", "bin", get_platform_arch()),
            extra_dirs=(xbmc.translatePath("special://xbmcbin"),))
        self._daemon.ensure_exec_permissions()
        self._port = self._enabled = None
        self._settings_path = os.path.join(kodi.ADDON_DATA, "settings.json")
        self._log_path = os.path.join(kodi.ADDON_DATA, "torrest.log")
        self._settings_spec = [s for s in kodi.get_all_settings_spec() if s["id"].startswith(
            self._settings_prefix + self._settings_separator)]
        self.onSettingsChanged()

    def _start(self):
        self._daemon.start(
            "-port", str(self._port), "-settings", self._settings_path, level=logging.INFO, path=self._log_path)

    def _stop(self):
        self._daemon.stop()

    def _request(self, method, url, **kwargs):
        return requests.request(method, "http://127.0.0.1:{}/{}".format(self._port, url), **kwargs)

    def _wait(self, timeout=-1, notification=False):
        start = time.time()
        while not 0 < timeout < time.time() - start:
            try:
                self._request("get", "")
                if notification:
                    kodi.notification(kodi.translate(30104))
                return
            except requests.exceptions.ConnectionError:
                if self.waitForAbort(0.5):
                    raise AbortRequestedError("Abort requested")
        raise DaemonTimeoutError("Timeout reached")

    def _get_kodi_settings(self):
        s = kodi.generate_dict_settings(self._settings_spec, separator=self._settings_separator)[self._settings_prefix]
        s["download_path"] = xbmc.translatePath(s["download_path"])
        s["torrents_path"] = os.path.join(s["download_path"], "Torrents")
        return s

    def _get_daemon_settings(self):
        r = self._request("get", self._settings_get_uri)
        if r.status_code != 200:
            logging.error("Failed getting daemon settings with code %d: %s", r.status_code, r.text)
            return None
        return r.json()

    def _update_kodi_settings(self):
        daemon_settings = self._get_daemon_settings()
        if daemon_settings is None:
            return False
        kodi.set_settings_dict(daemon_settings, prefix=self._settings_prefix, separator=self._settings_separator)
        return True

    def _update_daemon_settings(self):
        daemon_settings = self._get_daemon_settings()
        if daemon_settings is None:
            return False

        kodi_settings = self._get_kodi_settings()
        if daemon_settings != kodi_settings:
            logging.debug("Need to update daemon settings")
            r = self._request("post", self._settings_set_uri, json=kodi_settings)
            if r.status_code != 200:
                xbmcgui.Dialog().ok(kodi.translate(30102), r.json()["error"])
                return False

        return True

    def onSettingsChanged(self):
        with self._lock:
            port_changed = enabled_changed = False

            port = get_port()
            if port != self._port:
                self._port = port
                port_changed = True

            enabled = service_enabled()
            if enabled != self._enabled:
                self._enabled = enabled
                enabled_changed = True

            if self._enabled:
                if port_changed and not enabled_changed:
                    self._stop()
                if port_changed or enabled_changed:
                    self._start()
                    self._wait(timeout=get_daemon_timeout(), notification=True)
                self._update_daemon_settings()
            elif enabled_changed:
                self._stop()

    def handle_crashes(self, max_crashes=5, max_consecutive_crash_time=20):
        crash_count = 0
        last_crash = 0

        while not self.waitForAbort(1):
            # Initial check to avoid using the lock most of the time
            if self._daemon.daemon_poll() is None:
                continue

            with self._lock:
                if self._enabled and self._daemon.daemon_poll() is not None:
                    logging.info("Deamon crashed")
                    kodi.notification(kodi.translate(30105))
                    self._stop()

                    crash_time = time.time()
                    time_between_crashes = crash_time - last_crash
                    if 0 < max_consecutive_crash_time < time_between_crashes:
                        crash_count = 1
                    else:
                        crash_count += 1

                    if last_crash > 0:
                        logging.info("%s seconds passed since last crash", time_between_crashes)
                    last_crash = crash_time

                    if crash_count <= max_crashes:
                        logging.info("Re-starting daemon - %s/%s", crash_count, max_crashes)
                        self._start()
                        self._wait(timeout=get_daemon_timeout(), notification=True)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._stop()
        return exc_type is AbortRequestedError


@kodi.once("migrated")
def handle_first_run():
    logging.info("Handling first run")
    xbmcgui.Dialog().ok(kodi.translate(30100), kodi.translate(30101))
    kodi.open_settings()


def run():
    kodi.set_logger()
    handle_first_run()
    try:
        with DaemonMonitor() as monitor:
            monitor.handle_crashes()
    except DaemonNotFoundError:
        logging.info("Daemon not found. Aborting service...")
        if service_enabled():
            set_service_enabled(False)
            xbmcgui.Dialog().ok(kodi.ADDON_NAME, kodi.translate(30103))
            kodi.open_settings()
