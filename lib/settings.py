from lib.kodi import get_int_setting, get_boolean_setting, get_setting, set_boolean_setting


def get_port():
    return get_int_setting("port")


def get_daemon_timeout():
    return get_int_setting("timeout")


def get_metadata_timeout():
    return get_int_setting("metadata_timeout")


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


def run_as_root():
    return get_boolean_setting("run_as_root")


def set_service_enabled(value):
    set_boolean_setting("service_enabled", value)


def get_service_ip():
    return "127.0.0.1" if service_enabled() else get_setting("service_ip")


def download_after_insert():
    return get_boolean_setting("download_after_insert")


def get_files_order():
    return get_int_setting("files_order")


def show_background_progress():
    return get_boolean_setting("show_bg_progress")
