import logging
import os
import platform
import sys

from enum import Enum
from typing import NamedTuple


class System(Enum):
    linux = "linux"
    android = "android"
    darwin = "darwin"
    windows = "windows"


class Arch(Enum):
    x64 = "x64"
    x86 = "x86"
    arm = "arm"
    # arm64 = "arm64"
    armv7 = "armv7"


Platform = NamedTuple("Platform", [("system", System), ("version", str), ("arch", Arch)])


def get_platform():
    p = Platform(
        system=System(platform.system().lower()),
        version=platform.release(),
        arch=Arch.x64 if sys.maxsize > 2 ** 32 else Arch.x86,
    )

    machine = platform.machine()
    if "ANDROID_STORAGE" in os.environ:
        p.system = System.android
        if "arm" in machine or "aarch" in machine:
            p.arch = Arch.arm
    elif p.system == System.linux:
        if "armv7" in machine:
            p.arch = Arch.armv7
        elif "arm" in machine:
            p.arch = Arch.arm
    elif p.system == System.windows:
        if machine.endswith("64"):
            p.arch = Arch.x64
    elif p.system == System.darwin:
        p.arch = Arch.x64

    return p


def dump_platform():
    return "system: {}\nrelease: {}\nmachine: {}\narchitecture: {}\n".format(
        platform.system(), platform.release(), platform.machine(), platform.architecture())


try:
    PLATFORM = get_platform()
except Exception as _e:
    logging.fatal(_e)
    logging.fatal(dump_platform())


def get_platform_arch():
    return "{}_{}".format(PLATFORM.system.value, PLATFORM.arch.value)
