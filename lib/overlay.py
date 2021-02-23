import logging
import os

from xbmcgui import Window, ControlImage, ControlLabel

from lib.kodi import WINDOW_FULLSCREEN_VIDEO, ADDON_PATH, get_resolution
from lib.utils import assure_str


class OverlayText(object):
    def __init__(self, w=0.5, h=0.15, y_offset=0, label_padding=15, label_h=43):
        window_width, window_height = get_resolution()
        self._window = Window(WINDOW_FULLSCREEN_VIDEO)
        self._shown = False

        logging.debug("Using window width=%d and height=%d", window_width, window_height)
        total_label_h = 3 * label_h
        w = int(w * window_width)
        h = max(int(h * window_height), total_label_h + 2 * label_padding)
        x = (window_width - w) // 2
        y = int((3 * window_height / 4) - (h / 2) + 0.5) + y_offset

        label_x = x + label_padding
        label_w = w - 2 * label_padding
        label_y = y + int((h - total_label_h) / 2 + 0.5)
        self._label1 = ControlLabel(label_x, label_y, label_w, label_h, "", alignment=0x2 | 0x4)
        label_y += label_h
        self._label2 = ControlLabel(label_x, label_y, label_w, label_h, "", alignment=0x2 | 0x4)
        label_y += label_h
        self._label3 = ControlLabel(label_x, label_y, label_w, label_h, "", alignment=0x2 | 0x4)
        # ControlImage won't work with unicode special characters
        self._background = ControlImage(
            x, y, 0, 0, assure_str(os.path.join(ADDON_PATH, "resources", "images", "black.png")),
            colorDiffuse="0xD0000000")
        self._controls = [self._background, self._label1, self._label2, self._label3]
        self._window.addControls(self._controls)
        # We are only able to update visibility after adding elements, so to make them not visible
        # we have to create them with 0 width and height and then update the controls after adding
        # them to the window
        for c in self._controls:
            c.setVisible(self._shown)
        self._background.setWidth(w)
        self._background.setHeight(h)

    def _set_visible(self, visible):
        self._shown = visible
        for c in self._controls:
            c.setVisible(visible)

    def show(self):
        self._set_visible(True)

    def hide(self):
        self._set_visible(False)

    def set_text(self, label1=None, label2=None, label3=None):
        for label, control in ((label1, self._label1), (label2, self._label2), (label3, self._label3)):
            if label is not None:
                control.setLabel(label)

    def close(self):
        self._window.removeControls(self._controls)

    @property
    def shown(self):
        return self._shown
