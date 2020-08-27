import os

from lib.kodi import ADDON_DATA
from lib.service import run

if not os.path.exists(ADDON_DATA):
    os.makedirs(ADDON_DATA)

run()
