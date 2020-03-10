import logging
import os

import routing
from xbmcgui import ListItem
from xbmcplugin import addDirectoryItem, endOfDirectory

from lib.api import Torrest
from lib.dialog import DialogInsert
from lib.kodi import ADDON_PATH, translate, notification, set_logger, refresh
from lib.kodi_formats import is_music, is_picture, is_video
from lib.settings import get_port

plugin = routing.Plugin()
api = Torrest("localhost", get_port())


def li(tid, icon):
    return list_item(translate(tid), icon)


def list_item(label, icon):
    return ListItem(label, iconImage=os.path.join(ADDON_PATH, "resources", "images", icon))


def action(func, *args, **kwargs):
    return "RunPlugin({})".format(plugin.url_for(func, *args, **kwargs))


@plugin.route("/")
def index():
    addDirectoryItem(plugin.handle, plugin.url_for(torrents), li(30206, "torrents.png"), isFolder=True)
    addDirectoryItem(plugin.handle, plugin.url_for(dialog_insert), li(30207, "add.png"), isFolder=False)
    endOfDirectory(plugin.handle)


@plugin.route("/torrents")
def torrents():
    for torrent in api.torrents():
        torrent_li = list_item(torrent.name, "download.png")
        torrent_li.addContextMenuItems([
            (translate(30208), action(torrent_action, torrent.info_hash, "stop"))
            if torrent.status.total == torrent.status.total_wanted else
            (translate(30209), action(torrent_action, torrent.info_hash, "download")),
            (translate(30210), action(torrent_action, torrent.info_hash, "resume"))
            if torrent.status.paused else
            (translate(30211), action(torrent_action, torrent.info_hash, "pause")),
            (translate(30212), action(torrent_action, torrent.info_hash, "remove")),
        ])
        addDirectoryItem(plugin.handle, plugin.url_for(torrent_files, torrent.info_hash), torrent_li, isFolder=True)
    endOfDirectory(plugin.handle)


@plugin.route("/torrents/<info_hash>/<action_str>")
def torrent_action(info_hash, action_str):
    if action_str == "stop":
        api.stop_torrent(info_hash)
    elif action_str == "download":
        api.download_torrent(info_hash)
    elif action_str == "pause":
        api.pause_torrent(info_hash)
    elif action_str == "resume":
        api.resume_torrent(info_hash)
    elif action_str == "remove":
        api.remove_torrent(info_hash)
    else:
        logging.error("Unknown action '%s'", action_str)
        return
    refresh()


@plugin.route("/torrents/<info_hash>")
def torrent_files(info_hash):
    for f in api.files(info_hash):
        serve_url = api.serve_url(info_hash, f.id)
        file_li = list_item(f.name, "download.png")
        file_li.setProperty("IsPlayable", "true")
        file_li.setPath(serve_url)

        info_labels = {"title": f.name}
        if is_video(f.name):
            file_li.setInfo("video", info_labels)
        elif is_picture(f.name):
            file_li.setInfo("pictures", info_labels)
        elif is_music(f.name):
            file_li.setInfo("music", info_labels)

        file_li.addContextMenuItems([
            (translate(30209), action(file_action, info_hash, f.id, "download"))
            if f.status.priority == 0 else
            (translate(30208), action(file_action, info_hash, f.id, "stop")),
        ])

        addDirectoryItem(plugin.handle, serve_url, file_li)
    endOfDirectory(plugin.handle)


@plugin.route("/torrents/<info_hash>/files/<file_id>/<action_str>")
def file_action(info_hash, file_id, action_str):
    if action_str == "download":
        api.download_file(info_hash, file_id)
    elif action_str == "stop":
        api.stop_file(info_hash, file_id)
    else:
        logging.error("Unknown action '%s'", action_str)
        return
    refresh()


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
