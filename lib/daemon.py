import logging
import os
import shutil
import stat
import subprocess
import threading
from typing import Optional

from lib.os_platform import PLATFORM, System
from lib.utils import bytes_to_str, string_types


def android_get_current_app_id():
    with open("/proc/{:d}/cmdline".format(os.getpid())) as fp:
        return fp.read().rstrip("\0")


class Daemon(object):
    def __init__(self, name, daemon_dir):
        self._name = name
        if PLATFORM.system == System.windows:
            self._name += ".exe"

        self._dir = daemon_dir
        if PLATFORM.system == System.android:
            self._dir = os.path.join(os.sep, "data", "data", android_get_current_app_id(), "files", name)
            if not os.path.exists(self._dir):
                logging.info("Creating android destination folder '%s'", self._dir)
                os.makedirs(self._dir)

            src_path = os.path.join(daemon_dir, self._name)
            self._path = os.path.join(self._dir, self._name)
            if not os.path.exists(self._path) or self._get_sha1(src_path) != self._get_sha1(self._path):
                logging.info("Updating android daemon '%s'", self._path)
                shutil.copy(src_path, self._path)
        else:
            self._path = os.path.join(self._dir, self._name)

        self._p = None  # type: Optional[subprocess.Popen]
        self._logger = None  # type: Optional[threading.Thread]

    @staticmethod
    def _get_sha1(path):
        with open(path) as f:
            f.seek(-40, os.SEEK_END)
            return f.read()

    def ensure_exec_permissions(self):
        st = os.stat(self._path)
        if st.st_mode & stat.S_IEXEC != stat.S_IEXEC:
            logging.info("Setting exec permissions")
            os.chmod(self._path, st.st_mode | stat.S_IEXEC)

    def start_daemon(self, port=8080, settings="settings.json"):
        if not isinstance(port, int):
            raise ValueError("port must be an integer")
        if not isinstance(settings, string_types) or not settings:
            raise ValueError("settings must be a non empty string")
        if self._p is not None:
            raise ValueError("daemon already running")
        logging.info("Starting daemon on port %s with settings '%s'", port, settings)
        cmd = [self._path, "-port", str(port), "-settings", settings]
        self._p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=self._dir)

    def stop_daemon(self):
        if self._p is not None:
            logging.info("Terminating daemon")
            try:
                self._p.terminate()
            except OSError:
                logging.info("Daemon already terminated")
            self._p = None

    @staticmethod
    def _logger_job(fd, level=logging.INFO):
        for line in iter(fd.readline, fd.read(0)):
            logging.log(level, bytes_to_str(line).rstrip("\r\n"))

    def start_logger(self, level=logging.INFO):
        if self._logger is not None:
            raise ValueError("logger was already started")
        if self._p is None:
            raise ValueError("no process to log")
        logging.info("Starting daemon logger")
        self._logger = threading.Thread(target=self._logger_job, args=(self._p.stdout, level))
        self._logger.daemon = True
        self._logger.start()

    def stop_logger(self):
        if self._logger is None:
            raise ValueError("logger is already stopped")
        logging.info("Stopping daemon logger")
        self._logger.join()
        self._logger = None

    def start(self, port=8080, settings="settings.json", level=logging.INFO):
        self.start_daemon(port=port, settings=settings)
        self.start_logger(level=level)

    def stop(self):
        self.stop_daemon()
        self.stop_logger()
