import logging
import os
from functools import wraps
from xml.etree import ElementTree

import xbmc
import xbmcaddon
import xbmcgui

from lib.utils import PY3, assure_unicode, assure_str

# Windows IDs - https://kodi.wiki/view/Window_IDs
WINDOW_HOME = 10000
WINDOW_FULLSCREEN_VIDEO = 12005

ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo("name")
ADDON_ID = ADDON.getAddonInfo("id")
ADDON_PATH = assure_unicode(ADDON.getAddonInfo("path"))
ADDON_ICON = assure_unicode(ADDON.getAddonInfo("icon"))
ADDON_DATA = assure_unicode(xbmc.translatePath(ADDON.getAddonInfo("profile")))

set_setting = ADDON.setSetting
get_setting = ADDON.getSetting
open_settings = ADDON.openSettings

if PY3:
    translate = ADDON.getLocalizedString
else:
    def translate(*args, **kwargs):
        return ADDON.getLocalizedString(*args, **kwargs).encode("utf-8")


def notification(message, heading=ADDON_NAME, icon=ADDON_ICON, time=5000, sound=True):
    xbmcgui.Dialog().notification(heading, message, icon, time, sound)


def get_all_settings_spec():
    data = ElementTree.parse(os.path.join(ADDON_PATH, "resources", "settings.xml"))
    for element in data.findall("*/setting"):
        yield dict(element.attrib)


def get_setting_by_spec(spec):
    t = spec["type"]
    if t in ("number", "enum"):
        handle = get_int_setting
    elif t == "slider":
        # May be 'int', 'float' or 'percent'
        if spec.get("option") == "int":
            handle = get_int_setting
        else:
            handle = get_float_setting
    elif t == "bool":
        handle = get_boolean_setting
    else:
        handle = get_setting
    return handle(spec["id"])


def generate_dict_settings(settings_spec, separator=":"):
    settings_dict = {}

    for spec in settings_spec:
        obj = settings_dict
        keys = spec["id"].split(separator)

        for k in keys[:-1]:
            if k not in obj:
                obj[k] = {}
            obj = obj[k]

        obj[keys[-1]] = get_setting_by_spec(spec)

    return settings_dict


def set_settings_dict(settings_dict, prefix="", separator=":"):
    for k, v in settings_dict.items():
        if prefix:
            setting_id = prefix + separator + k
        else:
            setting_id = k
        if isinstance(v, dict):
            set_settings_dict(v, prefix=setting_id, separator=separator)
        else:
            set_any_setting(setting_id, v)


def get_boolean_setting(setting):
    return get_setting(setting) == "true"


def get_int_setting(setting):
    return int(get_setting(setting))


def get_float_setting(setting):
    return float(get_setting(setting))


def set_boolean_setting(setting, value):
    set_setting(setting, "true" if value else "false")


def set_any_setting(setting, value):
    if isinstance(value, bool):
        set_boolean_setting(setting, value)
    else:
        set_setting(setting, str(value))


def once(setting, default=False):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            if get_boolean_setting(setting) == default:
                set_boolean_setting(setting, not default)
                return function(*args, **kwargs)

        return wrapper

    return decorator


def refresh():
    xbmc.executebuiltin("Container.Refresh")


def show_picture(url):
    xbmc.executebuiltin('ShowPicture("{}")'.format(url))


def busy_dialog():
    xbmc.executebuiltin("ActivateWindow(busydialog)")


def close_busy_dialog():
    xbmc.executebuiltin("Dialog.Close(busydialog)")


def is_window_visible(window_id):
    return xbmc.getCondVisibility("Window.IsVisible({})".format(window_id))


def get_resolution():
    home = xbmcgui.Window(WINDOW_HOME)
    return home.getWidth(), home.getHeight()


class KodiLogHandler(logging.StreamHandler):
    levels = {
        logging.CRITICAL: xbmc.LOGFATAL,
        logging.ERROR: xbmc.LOGERROR,
        logging.WARNING: xbmc.LOGWARNING,
        logging.INFO: xbmc.LOGINFO if PY3 else xbmc.LOGNOTICE,
        logging.DEBUG: xbmc.LOGDEBUG,
        logging.NOTSET: xbmc.LOGNONE,
    }

    def __init__(self):
        super(KodiLogHandler, self).__init__()
        self.setFormatter(logging.Formatter("[{}] %(message)s".format(ADDON_ID)))

    def emit(self, record):
        xbmc.log(assure_str(self.format(record)), self.levels[record.levelno])

    def flush(self):
        pass


def set_logger(name=None, level=logging.NOTSET):
    logger = logging.getLogger(name)
    logger.handlers = [KodiLogHandler()]
    logger.setLevel(level)
