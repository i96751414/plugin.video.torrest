from lib.kodi import get_int_setting, get_boolean_setting, get_setting, set_boolean_setting


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


def ask_to_delete_torrent():
    return get_boolean_setting("ask_to_delete")


def service_enabled():
    return get_boolean_setting("service_enabled")


def set_service_enabled(value):
    set_boolean_setting("service_enabled", value)


def get_service_ip():
    return "127.0.0.1" if service_enabled() else get_setting("service_ip")
