import logging
import os
import time

import requests
import routing
from xbmc import Monitor, executebuiltin, getInfoLabel, getCondVisibility, sleep
from xbmcgui import ListItem, DialogProgress, Dialog
from xbmcplugin import addDirectoryItem, endOfDirectory, setResolvedUrl

from lib.api import Torrest, TorrestError
from lib.dialog import DialogInsert
from lib.kodi import ADDON_PATH, ADDON_NAME, translate, notification, set_logger, refresh, show_picture, \
    close_busy_dialog
from lib.kodi_formats import is_music, is_picture, is_video, is_text
from lib.player import TorrestPlayer
from lib.settings import get_service_ip, get_port, get_buffering_timeout, show_status_overlay, get_min_candidate_size, \
    ask_to_delete_torrent, download_after_insert, get_files_order, get_metadata_timeout
from lib.utils import sizeof_fmt

set_logger()
plugin = routing.Plugin()
api = Torrest(get_service_ip(), get_port())


class PlayError(Exception):
    def handle(self):
        pass


class CanceledError(PlayError):
    def __init__(self, e, info_hash):
        super(CanceledError, self).__init__(e)
        self._info_hash = info_hash

    def handle(self):
        handle_player_stop(self._info_hash)


def check_playable(func):
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as e:
            if not getattr(e, "%_checked", False):
                setResolvedUrl(plugin.handle, False, ListItem())
                if isinstance(e, PlayError):
                    logging.debug(e)
                    e.handle()
                    return
                setattr(e, "%_checked", True)
            raise e

    return wrapper


def check_directory(func):
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
            endOfDirectory(plugin.handle)
        except Exception as e:
            endOfDirectory(plugin.handle, succeeded=False)
            raise e

    return wrapper


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


def query_arg(name, required=True):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if name not in kwargs:
                query_list = plugin.args.get(name)
                if query_list:
                    kwargs[name] = query_list[0]
                elif required:
                    raise AttributeError("Missing {} required query argument".format(name))
            return func(*args, **kwargs)

        return wrapper

    return decorator


def get_state_string(state):
    if 0 <= state <= 9:
        return translate(30220 + state)
    return translate(30230)


def get_status_labels(info_hash):
    status = api.torrent_status(info_hash)
    return (
        "{:s} ({:.2f}%)".format(get_state_string(status.state), status.progress),
        "D:{:s}/s U:{:s}/s S:{:d}/{:d} P:{:d}/{:d}".format(
            sizeof_fmt(status.download_rate), sizeof_fmt(status.upload_rate), status.seeders,
            status.seeders_total, status.peers, status.peers_total))


def handle_player_stop(info_hash, name=None, initial_delay=0.5, listing_timeout=10):
    if not ask_to_delete_torrent():
        return
    try:
        info = api.torrent_info(info_hash)
    except TorrestError:
        return
    if name is None:
        name = info.name

    sleep(int(initial_delay * 1000))
    start_time = time.time()
    while getCondVisibility("Window.IsActive(busydialog)") and not 0 < listing_timeout < time.time() - start_time:
        sleep(100)

    remove_torrent = Dialog().yesno(ADDON_NAME, name + "\n" + translate(30241))
    if remove_torrent:
        api.remove_torrent(info_hash, delete=True)
        current_folder = getInfoLabel("Container.FolderPath")
        if current_folder == plugin.url_for(torrent_files, info_hash):
            executebuiltin("Action(Back)")
        elif current_folder == plugin.url_for(torrents):
            refresh()


@plugin.route("/")
def index():
    addDirectoryItem(plugin.handle, plugin.url_for(torrents), li(30206, "torrents.png"), isFolder=True)
    addDirectoryItem(plugin.handle, plugin.url_for(dialog_insert), li(30207, "add.png"), isFolder=False)
    endOfDirectory(plugin.handle)


@plugin.route("/torrents")
@check_directory
def torrents():
    for torrent in api.torrents():
        torrent_li = list_item(torrent.name, "download.png")
        torrent_li.addContextMenuItems([
            (translate(30235), media(play_info_hash, info_hash=torrent.info_hash)),
            (translate(30208), action(torrent_action, torrent.info_hash, "stop"))
            if torrent.status.total == torrent.status.total_wanted else
            (translate(30209), action(torrent_action, torrent.info_hash, "download")),
            (translate(30210), action(torrent_action, torrent.info_hash, "resume"))
            if torrent.status.paused else
            (translate(30211), action(torrent_action, torrent.info_hash, "pause")),
            (translate(30242), action(torrent_action, torrent.info_hash, "remove_torrent")),
            (translate(30212), action(torrent_action, torrent.info_hash, "remove_torrent_and_files")),
            (translate(30245), action(torrent_action, torrent.info_hash, "torrent_status"))
        ])
        addDirectoryItem(plugin.handle, plugin.url_for(torrent_files, torrent.info_hash), torrent_li, isFolder=True)


@plugin.route("/torrents/<info_hash>/<action_str>")
def torrent_action(info_hash, action_str):
    needs_refresh = True

    if action_str == "stop":
        api.stop_torrent(info_hash)
    elif action_str == "download":
        api.download_torrent(info_hash)
    elif action_str == "pause":
        api.pause_torrent(info_hash)
    elif action_str == "resume":
        api.resume_torrent(info_hash)
    elif action_str == "remove_torrent":
        api.remove_torrent(info_hash, delete=False)
    elif action_str == "remove_torrent_and_files":
        api.remove_torrent(info_hash, delete=True)
    elif action_str == "torrent_status":
        torrent_status(info_hash)
        needs_refresh = False
    else:
        logging.error("Unknown action '%s'", action_str)
        needs_refresh = False

    if needs_refresh:
        refresh()


def torrent_status(info_hash):
    status = api.torrent_status(info_hash)
    notification("{:s} ({:.2f}%)".format(get_state_string(status.state), status.progress),
                 api.torrent_info(info_hash).name, sound=False)


def sort_files(files):
    order = get_files_order()
    if order == 1:
        files.sort(key=lambda k: k.name)
    elif order == 2:
        files.sort(key=lambda k: k.length)


@plugin.route("/torrents/<info_hash>")
@check_directory
def torrent_files(info_hash):
    files = api.files(info_hash)
    sort_files(files)
    for f in files:
        serve_url = api.serve_url(info_hash, f.id)
        file_li = list_item(f.name, "download.png")
        file_li.setPath(serve_url)

        context_menu_items = []
        info_labels = {"title": f.name}
        if is_picture(f.name):
            url = plugin.url_for(display_picture, info_hash, f.id)
            file_li.setInfo("pictures", info_labels)
        elif is_text(f.name):
            url = plugin.url_for(display_text, info_hash, f.id)
        else:
            url = serve_url
            if is_video(f.name):
                info_type = "video"
            elif is_music(f.name):
                info_type = "music"
            else:
                info_type = None

            if info_type is not None:
                kwargs = dict(info_hash=info_hash, file_id=f.id)
                url = plugin.url_for(play, **kwargs)
                file_li.setInfo(info_type, info_labels)
                file_li.setProperty("IsPlayable", "true")
                context_menu_items.append((translate(30235), media(buffer_and_play, **kwargs)))

        context_menu_items.append(
            (translate(30209), action(file_action, info_hash, f.id, "download"))
            if f.status.priority == 0 else
            (translate(30208), action(file_action, info_hash, f.id, "stop"))
        )
        file_li.addContextMenuItems(context_menu_items)

        addDirectoryItem(plugin.handle, url, file_li)


@plugin.route("/display_picture/<info_hash>/<file_id>")
def display_picture(info_hash, file_id):
    show_picture(api.serve_url(info_hash, file_id))


@plugin.route("/display_text/<info_hash>/<file_id>")
def display_text(info_hash, file_id):
    r = requests.get(api.serve_url(info_hash, file_id))
    Dialog().textviewer(api.file_info(info_hash, file_id).name, r.text)


@plugin.route("/play_url")
@check_playable
@query_arg("url")
def play_url(url, buffer=True):
    r = requests.get(url, stream=True)
    info_hash = api.add_torrent_obj(r.raw, ignore_duplicate=True)
    play_info_hash(info_hash, buffer=buffer)


@plugin.route("/play_magnet")
@check_playable
@query_arg("magnet")
def play_magnet(magnet, buffer=True):
    info_hash = api.add_magnet(magnet, ignore_duplicate=True)
    play_info_hash(info_hash, buffer=buffer)


@plugin.route("/play_path")
@check_playable
@query_arg("path")
def play_file(path, buffer=True):
    info_hash = api.add_torrent(path, ignore_duplicate=True)
    play_info_hash(info_hash, buffer=buffer)


@plugin.route("/play_info_hash/<info_hash>")
@check_playable
def play_info_hash(info_hash, buffer=True):
    if not api.torrent_status(info_hash).has_metadata:
        wait_for_metadata(info_hash)

    files = api.files(info_hash, status=False)
    min_candidate_size = get_min_candidate_size() * 1024 * 1024
    candidate_files = [f for f in files if is_video(f.path) and f.length >= min_candidate_size]
    if not candidate_files:
        notification(translate(30239))
        raise PlayError("No candidate files found for {}".format(info_hash))
    elif len(candidate_files) == 1:
        chosen_file = candidate_files[0]
    else:
        sort_files(candidate_files)
        chosen_index = Dialog().select(translate(30240), [f.name for f in candidate_files])
        if chosen_index < 0:
            raise PlayError("User canceled dialog select")
        chosen_file = candidate_files[chosen_index]

    if buffer:
        buffer_and_play(info_hash, chosen_file.id)
    else:
        play(info_hash, chosen_file.id)


def wait_for_metadata(info_hash):
    close_busy_dialog()
    percent = 0
    timeout = get_metadata_timeout()
    start_time = time.time()
    monitor = Monitor()
    progress = DialogProgress()
    progress.create(ADDON_NAME, translate(30237))

    try:
        while not api.torrent_status(info_hash).has_metadata:
            if monitor.waitForAbort(0.5):
                raise PlayError("Abort requested")
            passed_time = time.time() - start_time
            if 0 < timeout:
                if timeout < passed_time:
                    notification(translate(30238))
                    raise PlayError("No metadata after timeout")
                percent = int(100 * passed_time / timeout)
            else:
                percent = 0 if percent == 100 else (percent + 5)
            progress.update(percent)
            if progress.iscanceled():
                raise CanceledError("User canceled metadata", info_hash)
    finally:
        progress.close()


@plugin.route("/buffer_and_play/<info_hash>/<file_id>")
@check_playable
def buffer_and_play(info_hash, file_id):
    api.download_file(info_hash, file_id, buffer=True)
    if api.file_status(info_hash, file_id).buffering_progress < 100:
        wait_for_buffering_completion(info_hash, file_id)
    play(info_hash, file_id)


def wait_for_buffering_completion(info_hash, file_id):
    close_busy_dialog()
    info = api.file_info(info_hash, file_id)
    of = translate(30244)
    timeout = get_buffering_timeout()
    last_time = last_done = 0
    start_time = time.time()

    monitor = Monitor()
    progress = DialogProgress()
    progress.create(ADDON_NAME)

    try:
        while True:
            current_time = time.time()
            status = api.file_status(info_hash, file_id)
            if status.buffering_progress >= 100:
                break

            total_done = status.buffering_total * status.buffering_progress / 100
            speed = float(total_done - last_done) / (current_time - last_time)
            last_time = current_time
            last_done = total_done
            progress.update(
                int(status.buffering_progress),
                "{} - {:.2f}%\n{} {} {} - {}/s\n{}\n".format(
                    get_state_string(status.state), status.buffering_progress, sizeof_fmt(total_done),
                    of, sizeof_fmt(status.buffering_total), sizeof_fmt(speed), info.name))

            if progress.iscanceled():
                raise CanceledError("User canceled buffering", info_hash)
            if 0 < timeout < current_time - start_time:
                notification(translate(30236))
                raise PlayError("Buffering timeout reached")
            if monitor.waitForAbort(1):
                raise PlayError("Abort requested")
    finally:
        progress.close()


@plugin.route("/play/<info_hash>/<file_id>")
@check_playable
def play(info_hash, file_id):
    serve_url = api.serve_url(info_hash, file_id)
    name = api.torrent_info(info_hash).name
    setResolvedUrl(plugin.handle, True, ListItem(name, path=serve_url))

    TorrestPlayer(
        url=serve_url,
        text_handler=(lambda: get_status_labels(info_hash) + (name,)) if show_status_overlay() else None,
        on_close_handler=lambda: handle_player_stop(info_hash, name=name),
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
        api.add_torrent(window.ret_val, download=download_after_insert())
    elif window.type == DialogInsert.TYPE_URL:
        api.add_magnet(window.ret_val, download=download_after_insert())
    else:
        return
    notification(translate(30243), time=2000)


def run():
    try:
        plugin.run()
    except Exception as e:
        logging.error("Caught exception:", exc_info=True)
        notification(str(e))
