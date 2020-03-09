import logging
import os

import routing
from xbmcgui import ListItem
from xbmcplugin import addDirectoryItem, endOfDirectory

from lib.api import Torrest
from lib.dialog import DialogInsert
from lib.kodi import ADDON_PATH, translate, notification, set_logger
from lib.settings import get_port

plugin = routing.Plugin()
api = Torrest("localhost", get_port())


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
    if window.type == DialogInsert.TYPE_PATH:
        api.add_torrent(window.ret_val)
    elif window.type == DialogInsert.TYPE_URL:
        api.add_magnet(window.ret_val)


def run():
    set_logger(level=logging.INFO)
    try:
        plugin.run()
    except Exception as e:
        logging.error("Caught exception:", exc_info=True)
        notification(str(e))
