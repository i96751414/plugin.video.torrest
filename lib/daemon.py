import logging
import os
import pipes
import re
import select
import shutil
import stat
import subprocess
import sys
import threading
from io import FileIO

from lib.os_platform import PLATFORM, System
from lib.utils import bytes_to_str, PY3


def get_current_app_id():
    with open("/proc/{:d}/cmdline".format(os.getpid())) as fp:
        return fp.read().rstrip("\0")


def join_cmd(cmd):
    return " ".join(pipes.quote(arg) for arg in cmd)


def read_select(fd, timeout):
    r, _, _ = select.select([fd], [], [], timeout)
    if fd not in r:
        raise SelectTimeoutError("Timed out waiting for pipe read")


# https://docs.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-sethandleinformation
HANDLE_FLAG_INHERIT = 0x00000001
# https://docs.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getfiletype
FILE_TYPE_DISK = 0x0001


def windows_suppress_file_handles_inheritance(r=0xFFFF):
    from ctypes import windll, wintypes, byref

    handles = []
    for handle in range(r):
        if windll.kernel32.GetFileType(handle) == FILE_TYPE_DISK:
            flags = wintypes.DWORD()
            if windll.kernel32.GetHandleInformation(handle, byref(flags)) and flags.value & HANDLE_FLAG_INHERIT:
                if windll.kernel32.SetHandleInformation(handle, HANDLE_FLAG_INHERIT, 0):
                    handles.append(handle)
                else:
                    logging.error("Error clearing inherit flag, disk file handle %x", handle)

    return handles


def windows_restore_file_handles_inheritance(handles):
    from ctypes import windll

    for handle in handles:
        if not windll.kernel32.SetHandleInformation(handle, HANDLE_FLAG_INHERIT, HANDLE_FLAG_INHERIT):
            logging.debug("Failed restoring handle %x inherit flag", handle)


class SelectTimeoutError(Exception):
    pass


class Pipe(object):
    def __init__(self):
        self._r, self._w = os.pipe()

    @property
    def r(self):
        return self._r

    @property
    def w(self):
        return self._w

    def read(self, buf, timeout=0):
        if self._r < 0:
            raise ValueError("read file descriptor is closed")
        if timeout > 0:
            read_select(self._r, timeout)
        return os.read(self._r, buf)

    def write(self, data):
        if self._w < 0:
            raise ValueError("write file descriptor is closed")
        return os.write(self._w, data)

    def close(self, read=False, write=False):
        both = not (read or write)
        if (both or read) and self._r >= 0:
            os.close(self._r)
            self._r = -1
        if (both or write) and self._w >= 0:
            os.close(self._w)
            self._w = -1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


class DefaultDaemonLogger(threading.Thread):
    def __init__(self, fd, default_level=logging.INFO, path=None):
        super(DefaultDaemonLogger, self).__init__()
        self.daemon = True
        self._fd = fd
        self._default_level = default_level
        self._file = open(path, "wb") if path else None
        self._stopped = False

    def _get_level_and_message(self, line):
        return self._default_level, line.rstrip("\r\n")

    def run(self):
        for line in iter(self._fd.readline, self._fd.read(0)):
            logging.log(*self._get_level_and_message(bytes_to_str(line)))
            if self._file:
                self._file.write(line)
                self._file.flush()
            if self._stopped:
                break

    def stop(self, timeout=None):
        self._stopped = True
        self.join(timeout)
        if self._file:
            self._file.close()


class DaemonLogger(DefaultDaemonLogger):
    levels_mapping = {
        "CRITICAL": logging.CRITICAL,
        "ERROR": logging.ERROR,
        "WARNING": logging.WARNING,
        "NOTICE": logging.INFO,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
    }

    tag_regex = re.compile("\x1b\\[[\\d;]+m")
    level_regex = re.compile(r"^(?:{})*\d+-\d+-\d+ \d+:\d+:\d+\.\d+ ({})".format(
        tag_regex.pattern, "|".join(levels_mapping)))

    def _get_level_and_message(self, line):
        m = self.level_regex.search(line)
        if m:
            line = line[len(m.group(0)):].lstrip(" ")
            level = self.levels_mapping[m.group(1)]
        else:
            level = self._default_level

        return level, self.tag_regex.sub("", line).rstrip("\r\n")


class DaemonNotFoundError(Exception):
    pass


class Daemon(object):
    def __init__(self, name, daemon_dir, work_dir=None, android_find_dest_dir=True,
                 android_extra_dirs=(), dest_dir=None, pid_file=None, root=False):
        self._name = name
        self._work_dir = work_dir
        self._pid_file = pid_file
        self._root = root
        self._root_pid = -1
        if PLATFORM.system == System.windows:
            self._name += ".exe"

        src_path = os.path.join(daemon_dir, self._name)
        if not os.path.exists(src_path):
            raise DaemonNotFoundError("Daemon source path does not exist: " + src_path)

        if PLATFORM.system == System.android and android_find_dest_dir:
            app_dir = os.path.join(os.sep, "data", "data", get_current_app_id())
            if not os.path.exists(app_dir):
                logging.debug("Default android app dir '%s' does not exist", app_dir)
                for directory in android_extra_dirs:
                    if os.path.exists(directory):
                        app_dir = directory
                        break

            logging.debug("Using android app dir '%s'", app_dir)
            self._dir = os.path.join(app_dir, "files", name)
        else:
            self._dir = dest_dir or daemon_dir
        self._path = os.path.join(self._dir, self._name)

        if self._dir is not daemon_dir:
            if not os.path.exists(self._path) or self._get_sha1(src_path) != self._get_sha1(self._path):
                logging.info("Updating %s daemon '%s'", PLATFORM.system, self._path)
                if os.path.exists(self._dir):
                    logging.debug("Removing old daemon dir %s", self._dir)
                    shutil.rmtree(self._dir)
                shutil.copytree(daemon_dir, self._dir)

        self._p = None  # type: subprocess.Popen or None
        self._logger = None  # type: DaemonLogger or None

    @staticmethod
    def _get_sha1(path):
        # Using FileIO instead of open as fseeko with OFF_T=64 is broken in android NDK
        # See https://trac.kodi.tv/ticket/17827
        with FileIO(path) as f:
            f.seek(-40, os.SEEK_END)
            return f.read()

    def kill_leftover_process(self):
        if self._pid_file and os.path.exists(self._pid_file):
            try:
                with open(self._pid_file) as f:
                    pid = int(f.read().rstrip("\r\n\0"))
                logging.warning("Killing process with pid %d", pid)
                self._kill(pid, 9)
            except Exception as e:
                logging.error("Failed killing process: %s", e)
            finally:
                os.remove(self._pid_file)

    def _kill(self, pid, signal):
        if self._root:
            if PLATFORM.system == System.android:
                subprocess.check_call(["su", "-c", "kill -{} {}".format(signal, pid)])
            else:
                logging.debug("Not possible to use root on this platform. Falling back to os.kill.")
                os.kill(pid, signal)
        else:
            os.kill(pid, signal)

    def ensure_exec_permissions(self):
        st = os.stat(self._path)
        if st.st_mode & stat.S_IEXEC != stat.S_IEXEC:
            logging.info("Setting exec permissions")
            os.chmod(self._path, st.st_mode | stat.S_IEXEC)

    def start_daemon(self, *args):
        if self._p is not None:
            raise ValueError("daemon already running")
        logging.info("Starting daemon with args: %s", args)
        cmd = [self._path] + list(args)
        work_dir = self._work_dir or self._dir
        kwargs = {}

        if PLATFORM.system == System.windows:
            if not PY3:
                # Attempt to solve https://bugs.python.org/issue1759845
                encoding = sys.getfilesystemencoding()
                for i, arg in enumerate(cmd):
                    cmd[i] = arg.encode(encoding)
                work_dir = work_dir.encode(encoding)
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE
            kwargs["startupinfo"] = si
            # Attempt to solve https://bugs.python.org/issue19575
            handles = windows_suppress_file_handles_inheritance()
        else:
            kwargs["close_fds"] = True
            # Make sure we update LD_LIBRARY_PATH, so libs are loaded
            env = os.environ.copy()
            ld_path = env.get("LD_LIBRARY_PATH", "")
            if ld_path:
                ld_path += os.pathsep
            ld_path += self._dir
            env["LD_LIBRARY_PATH"] = ld_path
            kwargs["env"] = env
            handles = []

        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.STDOUT
        kwargs["cwd"] = work_dir

        if self._root:
            if PLATFORM.system == System.android:
                cmd = ["su", "-c", "echo $$ && exec " + join_cmd(cmd)]
            else:
                logging.warning("Not possible to use root on this platform")

        logging.debug("Creating process with command %s and params %s", cmd, kwargs)
        try:
            self._p = subprocess.Popen(cmd, **kwargs)

            if self._root and PLATFORM.system == System.android:
                read_select(self._p.stdout.fileno(), 10)
                self._root_pid = int(self._p.stdout.readline().rstrip())

            if self._pid_file:
                logging.debug("Saving pid file %s", self._pid_file)
                with open(self._pid_file, "w") as f:
                    f.write(str(self._root_pid if self._root_pid >= 0 else self._p.pid))
        finally:
            if PLATFORM.system == System.windows:
                windows_restore_file_handles_inheritance(handles)

    def stop_daemon(self):
        if self._p is not None:
            logging.info("Terminating daemon")
            try:
                self._terminate()
            except (OSError, subprocess.CalledProcessError):
                logging.info("Daemon already terminated")
            if self._pid_file and os.path.exists(self._pid_file):
                os.remove(self._pid_file)
            self._root_pid = -1
            self._p = None

    def _terminate(self):
        if self._root and self._root_pid >= 0:
            if PLATFORM.system == System.android:
                subprocess.check_call(["su", "-c", "kill {}".format(self._root_pid)])
            else:
                logging.debug("Not possible to use root on this platform. Falling back to terminate.")
                self._p.terminate()
        else:
            self._p.terminate()

    def daemon_poll(self):
        return self._p and self._p.poll()

    @property
    def daemon_running(self):
        return self._p is not None and self._p.poll() is None

    def start_logger(self, level=logging.INFO, path=None):
        if self._logger is not None:
            raise ValueError("logger was already started")
        if self._p is None:
            raise ValueError("no process to log")
        logging.info("Starting daemon logger")
        self._logger = DaemonLogger(self._p.stdout, default_level=level, path=path)
        self._logger.start()

    def stop_logger(self):
        if self._logger is not None:
            logging.info("Stopping daemon logger")
            self._logger.stop()
            self._logger = None

    @property
    def logger_running(self):
        return self._logger is not None and self._logger.is_alive()

    def start(self, *args, **kwargs):
        self.start_daemon(*args)
        self.start_logger(**kwargs)

    def stop(self):
        self.stop_daemon()
        self.stop_logger()
