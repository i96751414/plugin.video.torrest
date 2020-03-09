from typing import NamedTuple, List  # NOQA

import requests

TorrentStatus = NamedTuple("TorrentStatus", [
    ("active_time", int),
    ("all_time_download", int),
    ("all_time_upload", int),
    ("download_rate", int),
    ("finished_time", int),
    ("has_metadata", bool),
    ("paused", bool),
    ("peers", int),
    ("peers_total", int),
    ("progress", int),
    ("seeders", int),
    ("seeders_total", int),
    ("seeding_time", int),
    ("state", int),
    ("total", int),
    ("total_done", int),
    ("total_wanted", int),
    ("total_wanted_done", int),
    ("upload_rate", int),
])

Torrent = NamedTuple("Torrent", [
    ("info_hash", str),
    ("name", str),
    ("size", int),
    ("status", TorrentStatus),
])


def from_dict(data, clazz, **converters):
    if data is None:
        return None
    # data = dict(data)
    for k, converter in converters.items():
        data[k] = converter(data.get(k))
    return clazz(**data)


class TorrestError(Exception):
    pass


class Torrest(object):
    def __init__(self, host, port):
        self._base_url = "http://{}:{}".format(host, port)
        self._session = requests.Session()

    def add_magnet(self, magnet):
        self._get("/add/magnet", params={"uri": magnet})

    def add_torrent(self, path):
        with open(path, "rb") as f:
            self._post("/add/torrent", files={"torrent": f})

    def torrents(self, status=True):
        """
        :type status: bool
        :rtype: List[Torrent]
        """
        for t in self._get("/torrents", params={"status": self._bool_str(status)}).json():
            yield from_dict(t, Torrent, status=lambda v: from_dict(v, TorrentStatus))

    def pause_torrent(self, info_hash):
        self._get("/torrents/{}/pause".format(info_hash))

    def resume_torrent(self, info_hash):
        self._get("/torrents/{}/resume".format(info_hash))

    def download_torrent(self, info_hash):
        self._get("/torrents/{}/download".format(info_hash))

    def stop_torrent(self, info_hash):
        self._get("/torrents/{}/stop".format(info_hash))

    def remove_torrent(self, info_hash, delete=True):
        self._get("/torrents/{}/remove".format(info_hash), params={"delete": self._bool_str(delete)})

    @staticmethod
    def _bool_str(value):
        return "true" if value else "false"

    def _post(self, url, **kwargs):
        return self._request("post", url, **kwargs)

    def _get(self, url, **kwargs):
        return self._request("get", url, **kwargs)

    def _request(self, method, url, validate=True, **kwargs):
        r = self._session.request(method, self._base_url + url, **kwargs)
        if validate and r.status_code >= 400:
            error = r.json()["error"]
            raise TorrestError(error)
        return r
