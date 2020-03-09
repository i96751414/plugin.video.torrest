from lib.kodi import get_int_setting


def get_port():
    return get_int_setting("port")
