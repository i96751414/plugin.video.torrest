import logging
from ctypes import cdll, Structure, c_uint16, c_char_p, c_int, c_size_t, string_at, c_bool, CFUNCTYPE
from threading import Thread


class String(Structure):
    _fields_ = [("ptr", c_char_p), ("size", c_size_t)]

    @classmethod
    def from_param(cls, obj):
        if not isinstance(obj, bytes):
            obj = obj.encode()
        return cls(obj, len(obj))

    def __bytes__(self):
        return string_at(self.ptr, self.size)

    def __str__(self):
        s = self.__bytes__()
        if not isinstance(s, str):
            s = s.decode()
        return s


class TorrestLib(object):
    LOG_LEVELS = [logging.DEBUG, logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL]
    LOG_CALLBACK = staticmethod(logging.log)
    DEFAULT_LOG_LEVEL = LOG_LEVELS.index(logging.INFO)

    def __init__(self, path):
        self._return_code = None
        self._thread = None

        # DLL specific
        self._dll = cdll.LoadLibrary(path)
        # Define start function
        self._dll.start.argtypes = [c_uint16, String, c_int]
        self._dll.start.restype = c_int
        # Define start_with_env function
        self._dll.start_with_env.restype = c_int
        # Define add_logging_file_sink function
        self._dll.add_logging_file_sink.argtypes = [String, c_bool]
        # Define add_logging_callback_sink callback
        self._c_log_callback = CFUNCTYPE(None, c_int, String)(self._log_callback)

    def start(self, port, settings_path, global_log_level=DEFAULT_LOG_LEVEL):
        self._return_code = None
        self._return_code = self._dll.start(port, settings_path, global_log_level)

    def start_with_env(self):
        self._return_code = None
        self._return_code = self._dll.start_with_env()

    def stop(self):
        self._dll.stop()

    def clear_logging_sinks(self):
        self._dll.clear_logging_sinks()

    def add_logging_stdout_sink(self):
        self._dll.add_logging_stdout_sink()

    def add_logging_file_sink(self, path, truncate=False):
        self._dll.add_logging_file_sink(path, truncate)

    def add_logging_callback_sink(self):
        self._dll.add_logging_callback_sink(self._c_log_callback)

    @classmethod
    def _log_callback(cls, level, string):
        if 0 <= level < len(cls.LOG_LEVELS):
            cls.LOG_CALLBACK(cls.LOG_LEVELS[level], string)

    def poll(self):
        if self._return_code is None and self._thread is not None and not self._thread.is_alive():
            self._return_code = -1
        return self._return_code

    def start_threaded(self, port, settings_path, global_log_level=DEFAULT_LOG_LEVEL, name=None, daemon=None):
        self._start_thread(self.start, (port, settings_path, global_log_level), name, daemon)

    def start_with_env_threaded(self, name=None, daemon=None):
        self._start_thread(self.start_with_env, (), name, daemon)

    def join_thread(self, timeout=None):
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None

    def _start_thread(self, target, args, name, daemon):
        if self._thread is None:
            self._return_code = None
            self._thread = Thread(name=name, target=target, args=args)
            if daemon is not None:
                self._thread.setDaemon(daemon)
            self._thread.start()
        else:
            raise RuntimeError("thread already started")
