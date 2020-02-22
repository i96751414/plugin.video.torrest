import sys

PY3 = sys.version_info.major >= 3

if PY3:
    def bytes_to_str(b):
        return b.decode()

else:
    def bytes_to_str(b):
        return b
