from lib.kodi import get_int_setting


def get_port():
    return get_int_setting("port")


def get_daemon_timeout():
    return get_int_setting("timeout")


def get_buffering_timeout():
    return get_int_setting("buffer_timeout")
