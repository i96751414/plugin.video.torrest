import logging
import os
import sys
import time

import routing
from xbmc import executebuiltin, Monitor
from xbmcgui import ListItem, DialogProgress, Dialog
from xbmcplugin import addDirectoryItem, endOfDirectory, setResolvedUrl

from lib.api import Torrest
from lib.dialog import DialogInsert
from lib.kodi import ADDON_PATH, ADDON_NAME, translate, notification, set_logger, refresh, show_picture
from lib.kodi_formats import is_music, is_picture, is_video
from lib.player import TorrestPlayer
from lib.settings import get_port, get_buffering_timeout, show_status_overlay

plugin = routing.Plugin()
api = Torrest("localhost", get_port())

MIN_CANDIDATE_SIZE = 100 * 1024 * 1024


def li(tid, icon):
    return list_item(translate(tid), icon)


def list_item(label, icon):
    item = ListItem(label)
    item.setArt({"icon": os.path.join(ADDON_PATH, "resources", "images", icon)})
    return item


def action(func, *args, **kwargs):
    return "RunPlugin({})".format(plugin.url_for(func, *args, **kwargs))


def media(func, *args, **kwargs):
    return "PlayMedia({})".format(plugin.url_for(func, *args, **kwargs))


def get_state_string(state):
    if 0 <= state <= 9:
        return translate(30220 + state)
    return translate(30230)


def sizeof_fmt(num, suffix="B", divisor=1000.0):
    for unit in ("", "k", "M", "G", "T", "P", "E", "Z"):
        if abs(num) < divisor:
            return "{:.2f}{}{}".format(num, unit, suffix)
        num /= divisor
    return "{:.2f}{}{}".format(num, "Y", suffix)


def get_status_string(info_hash, name):
    status = api.torrent_status(info_hash)
    return "{:s} ({:.2f}%)\nD:{:s}/s U:{:s}/s S:{:d}/{:d} P:{:d}/{:d}\n{:s}".format(
        get_state_string(status.state), status.progress, sizeof_fmt(status.download_rate),
        sizeof_fmt(status.upload_rate), status.seeders, status.seeders_total, status.peers, status.peers_total, name)


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
        file_li.setPath(serve_url)

        context_menu_items = []
        info_labels = {"title": f.name}
        if is_picture(f.name):
            url = plugin.url_for(display_picture, info_hash, f.id)
            file_li.setInfo("pictures", info_labels)
        else:
            url = serve_url
            if is_video(f.name):
                info_type = "video"
            elif is_music(f.name):
                info_type = "music"
            else:
                info_type = None

            if info_type is not None:
                url = plugin.url_for(play, info_hash, f.id)
                file_li.setInfo(info_type, info_labels)
                file_li.setProperty("IsPlayable", "true")
                context_menu_items.append((translate(30235), media(buffer_and_play, info_hash, f.id)))

        context_menu_items.append(
            (translate(30209), action(file_action, info_hash, f.id, "download"))
            if f.status.priority == 0 else
            (translate(30208), action(file_action, info_hash, f.id, "stop"))
        )
        file_li.addContextMenuItems(context_menu_items)

        addDirectoryItem(plugin.handle, url, file_li)
    endOfDirectory(plugin.handle)


@plugin.route("/display_picture/<info_hash>/<file_id>")
def display_picture(info_hash, file_id):
    show_picture(api.serve_url(info_hash, file_id))


@plugin.route("/play_magnet/<magnet>")
def play_magnet(magnet, timeout=30):
    if "?" not in magnet:
        magnet += sys.argv[2]

    start_time = time.time()
    info_hash = api.add_magnet(magnet, ignore_duplicate=True)
    monitor = Monitor()
    progress = DialogProgress()
    progress.create(ADDON_NAME, translate(30237))

    try:
        while not api.torrent_status(info_hash).has_metadata:
            if monitor.waitForAbort(0.5):
                logging.debug("Received abort request. Aborting...")
                return
            passed_time = time.time() - start_time
            if 0 < timeout < passed_time:
                raise ValueError("No metadata after timeout")
            progress.update(int(100 * passed_time / timeout))
            if progress.iscanceled():
                return
    finally:
        progress.close()

    files = api.files(info_hash, status=False)
    candidate_files = [f for f in files if is_video(f.path) and f.length >= MIN_CANDIDATE_SIZE]
    if not candidate_files:
        logging.info("No candidate files found from %s", info_hash)
        return
    elif len(candidate_files) == 1:
        chosen_file = candidate_files[0]
    else:
        chosen_index = Dialog().select(translate(30238), [f.name for f in candidate_files])
        if chosen_index < 0:
            return
        chosen_file = candidate_files[chosen_index]

    buffer_and_play(info_hash, chosen_file.id)


@plugin.route("/buffer_and_play/<info_hash>/<file_id>")
def buffer_and_play(info_hash, file_id):
    api.download_file(info_hash, file_id, buffer=True)

    monitor = Monitor()
    progress = DialogProgress()
    progress.create(ADDON_NAME)

    try:
        timeout = get_buffering_timeout()
        start_time = time.time()
        last_time = 0
        last_done = 0
        while True:
            current_time = time.time()
            status = api.file_status(info_hash, file_id)
            if status.buffering_progress >= 100:
                break

            speed = float(status.total_done - last_done) / (current_time - last_time)
            last_time = current_time
            last_done = status.total_done
            progress.update(
                int(status.buffering_progress),
                "{} - {:.2f}%".format(get_state_string(status.state), status.buffering_progress),
                "{} of {} - {}/s".format(sizeof_fmt(status.total_done), sizeof_fmt(status.total), sizeof_fmt(speed)))

            if progress.iscanceled():
                return
            if 0 < timeout < current_time - start_time:
                notification(translate(30236))
                return
            if monitor.waitForAbort(1):
                return
    finally:
        progress.close()

    play(info_hash, file_id)


@plugin.route("/play/<info_hash>/<file_id>")
def play(info_hash, file_id):
    if plugin.handle == -1:
        executebuiltin(media(play, info_hash, file_id))
        return

    serve_url = api.serve_url(info_hash, file_id)
    name = api.torrent_info(info_hash).name
    setResolvedUrl(plugin.handle, True, ListItem(name, path=serve_url))

    TorrestPlayer(
        url=serve_url,
        text_handler=(lambda: get_status_string(info_hash, name)) if show_status_overlay() else None,
    ).handle_events()


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
