import logging
import os

from xbmcgui import Window, ControlImage, ControlLabel

from lib.kodi import WINDOW_FULLSCREEN_VIDEO, ADDON_PATH, get_resolution


class OverlayText(object):
    def __init__(self, w=0.5, h=0.15, y_offset=0):
        window_width, window_height = get_resolution()
        self._window = Window(WINDOW_FULLSCREEN_VIDEO)
        self._shown = False

        logging.debug("Using window width=%d and height=%d", window_width, window_height)
        w = int(w * window_width)
        h = int(h * window_height)
        x = (window_width - w) // 2
        y = int((3 * window_height / 4) - (h / 2)) + y_offset

        self._label = ControlLabel(x, y, w, h, "", alignment=0x2 | 0x4)
        self._background = ControlImage(x, y, w, h, os.path.join(ADDON_PATH, "resources", "images", "black.png"))
        self._background.setColorDiffuse("0xD0000000")
        self._controls = [self._background, self._label]

    def show(self):
        if not self._shown:
            self._window.addControls(self._controls)
            self._shown = True

    def hide(self):
        if self._shown:
            self._window.removeControls(self._controls)
            self._shown = False

    def set_text(self, text):
        self._label.setLabel(text)

    @property
    def shown(self):
        return self._shown

    def __del__(self):
        self.hide()
