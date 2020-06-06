import sys

PY3 = sys.version_info.major >= 3

if PY3:
    string_types = str

    def str_to_bytes(s):
        return s.encode()

    def bytes_to_str(b):
        return b.decode()

    def assure_unicode(s):
        return s

    def assure_str(s):
        return s

else:
    # noinspection PyUnresolvedReferences
    string_types = basestring  # noqa

    def str_to_bytes(s):
        return s

    def bytes_to_str(b):
        return b

    def assure_unicode(s):
        if isinstance(s, str):
            # noinspection PyUnresolvedReferences
            s = s.decode("utf-8")
        return s

    def assure_str(s):
        # noinspection PyUnresolvedReferences
        if isinstance(s, unicode):  # noqa
            s = s.encode("utf-8")
        return s
