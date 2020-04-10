import logging
import os
import platform
import sys
from collections import namedtuple


class System:
    linux = "linux"
    android = "android"
    darwin = "darwin"
    windows = "windows"


class Arch:
    x64 = "x64"
    x86 = "x86"
    arm = "arm"
    arm64 = "arm64"
    armv7 = "armv7"


Platform = namedtuple("Platform", [
    "system",  # type:str
    "version",  # type:str
    "arch",  # type:str
])


def get_platform():
    system = platform.system().lower()
    version = platform.release()
    arch = Arch.x64 if sys.maxsize > 2 ** 32 else Arch.x86
    machine = platform.machine().lower()

    if "ANDROID_STORAGE" in os.environ:
        system = System.android
        if "arm" in machine or "aarch" in machine:
            if "64" in machine and arch == Arch.x64:
                arch = Arch.arm64
            else:
                arch = Arch.arm
    elif system == System.linux:
        if "armv7" in machine:
            arch = Arch.armv7
        elif "arm" in machine:
            if "64" in machine and arch == Arch.x64:
                arch = Arch.arm64
            else:
                arch = Arch.arm
    elif system == System.windows:
        if machine.endswith("64"):
            arch = Arch.x64
    elif system == System.darwin:
        arch = Arch.x64

    return Platform(system, version, arch)


def dump_platform():
    return "system: {}\nrelease: {}\nmachine: {}\narchitecture: {}\nmax_size: {}".format(
        platform.system(), platform.release(), platform.machine(), platform.architecture(), sys.maxsize)


try:
    PLATFORM = get_platform()
except Exception as _e:
    logging.fatal(_e, exc_info=True)
    logging.fatal(dump_platform())


def get_platform_arch():
    return "{}_{}".format(PLATFORM.system, PLATFORM.arch)
