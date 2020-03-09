import requests


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
