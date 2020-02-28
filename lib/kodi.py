import logging
import os
from xml.etree import ElementTree

import xbmc
import xbmcaddon

from lib.utils import PY3

ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo("path")
ADDON_NAME = ADDON.getAddonInfo("name")
ADDON_ID = ADDON.getAddonInfo("id")
ADDON_ICON = ADDON.getAddonInfo("icon")
ADDON_DATA = xbmc.translatePath(ADDON.getAddonInfo("profile"))

set_setting = ADDON.setSetting
get_setting = ADDON.getSetting
open_settings = ADDON.openSettings

if PY3:
    translate = ADDON.getLocalizedString
else:
    # noinspection PyUnresolvedReferences
    ADDON_PATH = ADDON_PATH.decode("utf-8")
    # noinspection PyUnresolvedReferences
    ADDON_DATA = ADDON_DATA.decode("utf-8")
    # noinspection PyUnresolvedReferences
    ADDON_ICON = ADDON_ICON.decode("utf-8")

    def translate(*args, **kwargs):
        return ADDON.getLocalizedString(*args, **kwargs).encode("utf-8")


def get_all_settings_spec():
    with open(os.path.join(ADDON_PATH, "resources", "settings.xml"), "rb") as f:
        data = ElementTree.XML(f.read())
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
            set_setting(setting_id, setting_to_str(v))


def get_boolean_setting(setting):
    return get_setting(setting) == "true"


def get_int_setting(setting):
    return int(get_setting(setting))


def get_float_setting(setting):
    return float(get_setting(setting))


def setting_to_str(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


class KodiLogHandler(logging.StreamHandler):
    levels = {
        logging.CRITICAL: xbmc.LOGFATAL,
        logging.ERROR: xbmc.LOGERROR,
        logging.WARNING: xbmc.LOGWARNING,
        logging.INFO: xbmc.LOGINFO,
        logging.DEBUG: xbmc.LOGDEBUG,
        logging.NOTSET: xbmc.LOGNONE,
    }

    def __init__(self):
        super(KodiLogHandler, self).__init__()
        self.setFormatter(logging.Formatter("[{}] %(message)s".format(ADDON_ID)))

    def emit(self, record):
        xbmc.log(self.format(record), self.levels[record.levelno])

    def flush(self):
        pass


def set_logger(name=None, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.addHandler(KodiLogHandler())
    logger.setLevel(level)
