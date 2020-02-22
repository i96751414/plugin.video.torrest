from lib.os_platform import PLATFORM


def get_platform_arch():
    return "{}_{}".format(PLATFORM.system.value, PLATFORM.arch.value)


def run():
    pass
