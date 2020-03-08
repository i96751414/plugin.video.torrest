import logging
import os

import routing
from xbmcgui import ListItem
from xbmcplugin import addDirectoryItem, endOfDirectory

from lib.dialog import DialogInsert
from lib.kodi import ADDON_PATH, translate, notification, set_logger

plugin = routing.Plugin()


def li(tid, icon):
    return ListItem(translate(tid), iconImage=os.path.join(ADDON_PATH, "resources", "images", icon))


@plugin.route("/")
def index():
    addDirectoryItem(plugin.handle, plugin.url_for(torrents), li(30206, "torrents.png"), isFolder=True)
    addDirectoryItem(plugin.handle, plugin.url_for(dialog_insert), li(30207, "add.png"), isFolder=False)
    endOfDirectory(plugin.handle)


@plugin.route("/torrents")
def torrents():
    # TODO
    endOfDirectory(plugin.handle)


@plugin.route("/insert")
def dialog_insert():
    window = DialogInsert("DialogInsert.xml", ADDON_PATH, "Default")
    window.doModal()
    # TODO
    if window.type == DialogInsert.TYPE_PATH:
        pass
    elif window.type == DialogInsert.TYPE_URL:
        pass


def run():
    set_logger(level=logging.INFO)
    try:
        plugin.run()
    except Exception as e:
        logging.error("Caught exception:", exc_info=True)
        notification(str(e))
