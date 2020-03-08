from xbmcgui import Dialog, WindowXMLDialog, ACTION_PARENT_DIR, ACTION_NAV_BACK, ACTION_PREVIOUS_MENU

from lib.kodi import ADDON_NAME, translate
from lib.utils import str_to_unicode


# noinspection PyUnresolvedReferences
class DialogInsert(WindowXMLDialog):
    TYPE_UNKNOWN = 0
    TYPE_URL = 1
    TYPE_PATH = 2

    def __init__(self, *args, **kwargs):
        super(DialogInsert, self).__init__(*args, **kwargs)
        self._ret_val = {self.TYPE_URL: "", self.TYPE_PATH: ""}
        self._type = self.TYPE_UNKNOWN

    def onInit(self):
        self._set_type(self.TYPE_URL)

    def onClick(self, control_id):
        if control_id == 32500:
            # Close Button
            self._cancelled()
        elif control_id == 32501:
            # Radio Button 1
            self._set_type(self.TYPE_URL)
        elif control_id == 32502:
            # Radio Button 2
            self._set_type(self.TYPE_PATH)
        elif control_id == 32508:
            # OK button
            self._ok()
        elif control_id == 32505:
            # Input button
            if self._type == self.TYPE_URL:
                self._set_url()
            elif self._type == self.TYPE_PATH:
                self._set_path()

    def onAction(self, action):
        if action.getId() in (ACTION_PARENT_DIR, ACTION_NAV_BACK, ACTION_PREVIOUS_MENU):
            self._cancelled()

    def _set_type(self, t):
        self.getControl(32501).setSelected(t == self.TYPE_URL)  # Radio Button 1
        self.getControl(32502).setSelected(t == self.TYPE_PATH)  # Radio Button 2
        self.getControl(32504).setLabel(translate(30203 if t == self.TYPE_URL else 30204))  # Box label
        self._type = t
        label = self._ret_val[t]
        self.getControl(32505).setLabel(label if label else " ")

    def _set_url(self):
        url = Dialog().input(ADDON_NAME)
        if url != "":
            self.getControl(32505).setLabel(url)
            self._ret_val[self.TYPE_URL] = url

    def _set_path(self):
        fn = str_to_unicode(Dialog().browse(1, ADDON_NAME, "files", ".torrent"))
        if fn != "":
            self.getControl(32505).setLabel(fn)
            self._ret_val[self.TYPE_PATH] = fn

    def _cancelled(self):
        self._type = self.TYPE_UNKNOWN
        self.close()

    def _ok(self):
        self.close()

    @property
    def ret_val(self):
        return self._ret_val.get(self._type)

    @property
    def type(self):
        return self._type
