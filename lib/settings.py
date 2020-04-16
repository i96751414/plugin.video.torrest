from lib.kodi import get_int_setting, get_boolean_setting


def get_port():
    return get_int_setting("port")


def get_daemon_timeout():
    return get_int_setting("timeout")


def get_buffering_timeout():
    return get_int_setting("buffer_timeout")


def show_status_overlay():
    return get_boolean_setting("overlay")


def get_min_candidate_size():
    return get_int_setting("min_candidate_size")
