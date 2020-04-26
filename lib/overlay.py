import logging
import os

from xbmcgui import Window, ControlImage, ControlLabel

from lib.kodi import WINDOW_FULLSCREEN_VIDEO, ADDON_PATH, get_resolution


class OverlayText(object):
    def __init__(self, w=0.5, h=0.15, y_offset=0, label_padding=15):
        window_width, window_height = get_resolution()
        self._window = Window(WINDOW_FULLSCREEN_VIDEO)
        self._shown = False

        logging.debug("Using window width=%d and height=%d", window_width, window_height)
        w = int(w * window_width)
        h = int(h * window_height)
        x = (window_width - w) // 2
        y = int((3 * window_height / 4) - (h / 2)) + y_offset

        self._label = ControlLabel(x + label_padding, y + label_padding, 0, 0, "", alignment=0x2 | 0x4)
        self._background = ControlImage(
            x, y, 0, 0, os.path.join(ADDON_PATH, "resources", "images", "black.png"),
            colorDiffuse="0xD0000000")
        self._controls = [self._background, self._label]
        self._window.addControls(self._controls)
        # We are only able to update visibility after adding elements, so to make them not visible
        # we have to create them with 0 width and height and then update the controls after adding
        # them to the window
        for c in self._controls:
            c.setVisible(self._shown)
        self._background.setWidth(w)
        self._background.setHeight(h)
        self._label.setWidth(w - 2 * label_padding)
        self._label.setHeight(h - 2 * label_padding)

    def _set_visible(self, visible):
        self._shown = visible
        for c in self._controls:
            c.setVisible(visible)

    def show(self):
        self._set_visible(True)

    def hide(self):
        self._set_visible(False)

    def set_text(self, text):
        self._label.setLabel(text)

    def close(self):
        self._window.removeControls(self._controls)

    @property
    def shown(self):
        return self._shown
