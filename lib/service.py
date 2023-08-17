import logging
import os
import shutil
import threading
import time

import requests
import xbmc
import xbmcgui

from lib import kodi
from lib.os_platform import get_platform_arch, get_shared_lib_extension, get_executable_extension
from lib.settings import get_port, get_daemon_timeout, service_enabled, set_service_enabled, get_service_address, \
    show_background_progress, set_has_libtorrest, get_force_torrest, ssl_enabled
from lib.torrest.api import Torrest, STATUS_FINISHED, STATUS_SEEDING, STATUS_PAUSED
from lib.torrest_daemon import TorrestLibraryDaemon, TorrestExecutableDaemon, TorrestDaemonNotFoundError
from lib.utils import sizeof_fmt, assure_unicode

BASE_DIRECTORY = os.path.join(kodi.ADDON_PATH, "resources", "bin", get_platform_arch())
LIB_NAME = "libtorrest" + get_shared_lib_extension()
LIB_PATH = os.path.join(BASE_DIRECTORY, LIB_NAME)


class AbortRequestedError(Exception):
    pass


class DaemonTimeoutError(Exception):
    pass


class DaemonMonitor(xbmc.Monitor):
    _settings_prefix = "s"
    _settings_separator = ":"
    _settings_get_uri = "settings"
    _settings_set_uri = "settings?reset=true"

    settings_name = "settings.json"
    log_name = "torrest.log"

    def __init__(self):
        super(DaemonMonitor, self).__init__()
        self._lock = threading.Lock()
        self._settings_path = os.path.join(kodi.ADDON_DATA, self.settings_name)
        self._log_path = os.path.join(kodi.ADDON_DATA, self.log_name)
        self._enabled = None
        self._settings_spec = [s for s in kodi.get_all_settings_spec() if s["id"].startswith(
            self._settings_prefix + self._settings_separator)]

        logging.info("Using '%s' as torrest base directory", BASE_DIRECTORY)
        config = dict(settings_path=self._settings_path, log_path=self._log_path, port=None)
        kwargs = dict(config=config, dest_dir=os.path.join(kodi.ADDON_DATA, "bin"), work_dir=kodi.ADDON_DATA,
                      android_extra_dirs=(kodi.translatePath("special://xbmcbin"),))

        if os.path.exists(LIB_PATH) and not get_force_torrest():
            logging.info("Configuring torrest libray (%s)", LIB_NAME)
            self._daemon = TorrestLibraryDaemon(LIB_NAME, BASE_DIRECTORY, **kwargs)
        else:
            exe_name = "torrest" + get_executable_extension()
            logging.info("Configuring torrest executable (%s)", exe_name)
            self._daemon = TorrestExecutableDaemon(
                exe_name, BASE_DIRECTORY, pid_file=os.path.join(kodi.ADDON_DATA, ".pid"), **kwargs)

    def _request(self, method, url, **kwargs):
        return requests.request(method, "http://127.0.0.1:{}/{}".format(self._daemon.get_config("port"), url), **kwargs)

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
        s["download_path"] = assure_unicode(kodi.translatePath(s["download_path"]))
        s["torrents_path"] = assure_unicode(kodi.translatePath(s["torrents_path"]))
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
            r = self._request("put", self._settings_set_uri, json=kodi_settings)
            if r.status_code != 200:
                xbmcgui.Dialog().ok(kodi.translate(30102), r.json()["error"])
                return False

        return True

    def onSettingsChanged(self):
        with self._lock:
            port_changed = enabled_changed = False

            port = get_port()
            if port != self._daemon.get_config("port"):
                self._daemon.set_config("port", port)
                port_changed = True

            enabled = service_enabled()
            if enabled != self._enabled:
                self._enabled = enabled
                enabled_changed = True

            if self._enabled:
                if port_changed and not enabled_changed:
                    self._daemon.stop()
                if port_changed or enabled_changed:
                    self._daemon.start()
                    self._wait(timeout=get_daemon_timeout(), notification=True)
                self._update_daemon_settings()
            elif enabled_changed:
                self._daemon.stop()

    def handle_crashes(self, max_crashes=5, max_consecutive_crash_time=20):
        crash_count = 0
        last_crash = 0

        while not self.waitForAbort(1):
            # Initial check to avoid using the lock most of the time
            if self._daemon.poll() is None:
                continue

            with self._lock:
                if self._enabled and self._daemon.poll() is not None:
                    logging.warning("Deamon crashed")
                    kodi.notification(kodi.translate(30105))
                    self._daemon.stop()

                    if os.path.exists(self._log_path):
                        path = os.path.join(kodi.ADDON_DATA, time.strftime("%Y%m%d_%H%M%S.") + self.log_name)
                        shutil.copy(self._log_path, path)

                    crash_time = time.time()
                    time_between_crashes = crash_time - last_crash
                    if 0 < max_consecutive_crash_time < time_between_crashes:
                        crash_count = 1
                    else:
                        crash_count += 1

                    if last_crash > 0:
                        logging.info("%.2f seconds passed since last crash", time_between_crashes)
                    last_crash = crash_time

                    if crash_count <= max_crashes:
                        logging.info("Re-starting daemon - %s/%s", crash_count, max_crashes)

                        if crash_count > 1 and os.path.exists(self._settings_path):
                            logging.info("Removing old settings file")
                            os.remove(self._settings_path)

                        self._daemon.start()

                        try:
                            self._wait(timeout=get_daemon_timeout(), notification=True)
                            self._update_daemon_settings()
                        except DaemonTimeoutError:
                            logging.error("Timed out waiting for daemon")
                            last_crash = time.time()
                    else:
                        logging.info("Max crashes (%d) reached", max_crashes)
                        return

    def start(self):
        self._daemon.setup()
        try:
            self.onSettingsChanged()
        except DaemonTimeoutError:
            logging.error("Timed out waiting for daemon")

    def stop(self):
        self._daemon.stop()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return exc_type is AbortRequestedError


class DownloadProgress(xbmc.Monitor, threading.Thread):
    def __init__(self):
        xbmc.Monitor.__init__(self)
        threading.Thread.__init__(self)
        self.daemon = True
        self._api = self._enabled = self._dialog = None
        self._index = 0
        self.onSettingsChanged()

    def run(self):
        while not self.waitForAbort(5):
            if self._enabled:
                try:
                    self._update_progress()
                except requests.exceptions.ConnectionError:
                    self._close_dialog()
                    logging.debug("Failed to update background progress")
            else:
                self._close_dialog()
        self._close_dialog()

    def _update_progress(self):
        torrents = [t for t in self._api.torrents() if t.status.state not in (
            STATUS_FINISHED, STATUS_SEEDING, STATUS_PAUSED)]
        torrents_count = len(torrents)

        if torrents_count > 0:
            if self._index >= torrents_count:
                download_rate = sum(t.status.download_rate for t in torrents)
                upload_rate = sum(t.status.upload_rate for t in torrents)
                progress = sum(t.status.progress for t in torrents) / torrents_count
                name = kodi.translate(30106)
                self._index = 0
            else:
                download_rate = torrents[self._index].status.download_rate
                upload_rate = torrents[self._index].status.upload_rate
                progress = torrents[self._index].status.progress
                name = torrents[self._index].name
                if len(name) > 30:
                    name = name[:30] + "..."
                self._index += 1

            message = "{} - D:{}/s U:{}/s".format(name, sizeof_fmt(download_rate), sizeof_fmt(upload_rate))
            self._get_dialog().update(int(progress), kodi.ADDON_NAME, message)
        else:
            self._close_dialog()

    def _get_dialog(self):
        if self._dialog is None:
            self._dialog = xbmcgui.DialogProgressBG()
            self._dialog.create(kodi.ADDON_NAME)
        return self._dialog

    def _close_dialog(self):
        if self._dialog is not None:
            self._dialog.close()
            self._dialog = None

    def onSettingsChanged(self):
        self._api = Torrest(get_service_address(), get_port(), ssl_enabled())
        self._enabled = show_background_progress()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.join()
        return False


@kodi.once("migrated")
def handle_first_run():
    logging.info("Handling first run")
    xbmcgui.Dialog().ok(kodi.translate(30100), kodi.translate(30101))
    kodi.open_settings()


def run():
    kodi.set_logger()
    set_has_libtorrest(os.path.exists(LIB_PATH))
    handle_first_run()

    try:
        with DaemonMonitor() as monitor:
            with DownloadProgress():
                monitor.handle_crashes()
    except TorrestDaemonNotFoundError as e:
        logging.info("Daemon not found. Aborting service (%s).", e)
        if service_enabled():
            set_service_enabled(False)
            xbmcgui.Dialog().ok(kodi.ADDON_NAME, kodi.translate(30103))
            kodi.open_settings()
