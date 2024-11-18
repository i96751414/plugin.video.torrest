from lib.kodi import get_int_setting, get_boolean_setting, get_setting, set_boolean_setting


class FilesOrder:
    ID = 0
    NAME = 1
    SIZE = 2


class PlaybackStopAction:
    ASK_TO_DELETE = 0
    DELETE = 1
    IGNORE = 2


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


def get_on_playback_stop_action():
    return get_int_setting("on_playback_stop")


def service_enabled():
    return get_boolean_setting("service_enabled")


def ssl_enabled():
    return get_boolean_setting("ssl_connection")


def set_service_enabled(value):
    set_boolean_setting("service_enabled", value)


def get_service_address():
    return "127.0.0.1" if service_enabled() else get_setting("service_address")


def download_after_insert():
    return get_boolean_setting("download_after_insert")


def folder_listing_enabled():
    return get_boolean_setting("enable_folders")


def skip_root_folder():
    return get_boolean_setting("skip_root_folder")


def get_files_order():
    return get_int_setting("files_order")


def show_background_progress():
    return get_boolean_setting("show_bg_progress")


def set_has_libtorrest(value):
    set_boolean_setting("has_libtorrest", value)


def get_force_torrest():
    return get_boolean_setting("force_torrest")
