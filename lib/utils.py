import sys

PY3 = sys.version_info.major >= 3

if PY3:
    string_types = str

    def str_to_bytes(s):
        return s.encode()

    def bytes_to_str(b):
        return b.decode()

    def str_to_unicode(s):
        return s

    def unicode_to_str(s):
        return s

else:
    # noinspection PyUnresolvedReferences
    string_types = basestring  # noqa

    def str_to_bytes(s):
        return s

    def bytes_to_str(b):
        return b

    def str_to_unicode(s):
        return s.decode("utf-8")

    def unicode_to_str(s):
        return s.encode("utf-8")
