import logging
import threading
import time

import xbmc

from lib.overlay import OverlayText


def _execute_callback(callback):
    logging.debug("Calling %s callback", callback.__name__)
    try:
        callback()
    except Exception as e:
        logging.error("Exception thrown when executing callback %s: %s", callback.__name__, e, exc_info=True)


class PlayerTimeoutError(Exception):
    pass


class PlayerUrlError(Exception):
    pass


class Player(object):
    def __init__(self):
        super(Player, self).__init__()
        self._monitor = xbmc.Monitor()
        self._player = xbmc.Player()

    def handle_events(self, url=None, timeout=60, period=0.2):
        start_time = time.time()
        while True:
            if self.is_active():
                if not url:
                    break
                playing_file = self.get_playing_file()
                if playing_file == url:
                    break
                elif playing_file:
                    raise PlayerUrlError("Expecting url '%s' but found '%s'. Aborting...", url, playing_file)

            if 0 < timeout < time.time() - start_time:
                raise PlayerTimeoutError("Player did not start after {} seconds".format(timeout))
            if self._monitor.waitForAbort(0.5):
                logging.debug("Received abort request. Aborting...")
                return

        current_event = 0
        events = [
            (0, self.is_playing, self.on_playback_resumed),
            (1, self.is_paused, self.on_playback_paused),
        ]

        _execute_callback(self.on_playback_started)
        while self.is_active() and (not url or self.get_playing_file() == url):
            for event, handle, callback in events:
                if handle():
                    if current_event != event:
                        current_event = event
                        _execute_callback(callback)
                    break
            if self._monitor.waitForAbort(period):
                _execute_callback(self.on_abort_requested)
                return

        _execute_callback(self.on_playback_stopped)

    def get_playing_file(self):
        return self._player.getPlayingFile()

    def is_active(self):
        return self._player.isPlaying()

    @staticmethod
    def is_paused():
        return xbmc.getCondVisibility("Player.Paused")

    @staticmethod
    def is_playing():
        return xbmc.getCondVisibility("Player.Playing")

    def on_playback_started(self):
        pass

    def on_playback_paused(self):
        pass

    def on_playback_resumed(self):
        pass

    def on_playback_stopped(self):
        pass

    def on_abort_requested(self):
        pass


class TorrestPlayer(Player):
    def __init__(self, text_handler=None, on_close_handler=None):
        super(TorrestPlayer, self).__init__()
        self._stopped = False
        self._text_handler = text_handler
        self._on_close_handler = on_close_handler
        self._overlay = self._overlay_thread = None

    # noinspection PyAttributeOutsideInit
    def on_playback_started(self):
        if self._text_handler:
            self._overlay = OverlayText()
            self._overlay_thread = threading.Thread(target=self._overlay_updater)
            self._overlay_thread.daemon = True
            self._overlay_thread.start()

    def on_playback_paused(self):
        if self._overlay:
            self._overlay.show()
            self._update_overlay_text()

    def on_playback_resumed(self):
        if self._overlay:
            self._overlay.hide()

    def on_playback_stopped(self):
        self._stopped = True
        if self._on_close_handler:
            self._on_close_handler()

    def on_abort_requested(self):
        self._stopped = True

    def _update_overlay_text(self):
        self._overlay.set_text(*self._text_handler())

    def _overlay_updater(self):
        while not self._stopped:
            if self._overlay.shown:
                self._update_overlay_text()
            if self._monitor.waitForAbort(1):
                break
        self._overlay.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._stopped = True
        if self._overlay:
            self._overlay_thread.join()
            self._overlay.close()
        return False
