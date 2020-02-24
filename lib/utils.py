import sys

PY3 = sys.version_info.major >= 3

if PY3:
    string_types = str


    def bytes_to_str(b):
        return b.decode()

else:
    # noinspection PyUnresolvedReferences
    string_types = basestring


    def bytes_to_str(b):
        return b
