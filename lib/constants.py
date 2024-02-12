import logging
import os
import platform
import sys


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


SHARED_LIB_EXTENSIONS = {System.linux: ".so", System.android: ".so", System.darwin: ".dylib", System.windows: ".dll"}
EXECUTABLE_EXTENSIONS = {System.windows: ".exe"}


def get_platform():
    system = platform.system().lower()
    version = platform.release()
    arch = Arch.x64 if sys.maxsize > 2 ** 32 else Arch.x86
    machine = platform.machine().lower()
    is_arch64 = "64" in machine and arch == Arch.x64

    logging.debug("Resolving platform - system=%s, version=%s, arch=%s, machine=%s", system, version, arch, machine)

    if "ANDROID_STORAGE" in os.environ:
        system = System.android
        if "arm" in machine or "aarch" in machine:
            arch = Arch.arm64 if is_arch64 else Arch.arm
    elif system == System.linux:
        if "armv7" in machine:
            arch = Arch.armv7
        elif "aarch" in machine:
            arch = Arch.arm64 if is_arch64 else Arch.armv7
        elif "arm" in machine:
            arch = Arch.arm64 if is_arch64 else Arch.arm
    elif system == System.windows:
        if machine.endswith("64"):
            arch = Arch.x64
    elif system == System.darwin:
        arch = Arch.x64

    return system, arch


SYSTEM, ARCH = get_platform()
PLATFORM = "{system}_{arch}".format(system=SYSTEM, arch=ARCH)
LIB_NAME = "libtorrest{lib_extension}".format(lib_extension=SHARED_LIB_EXTENSIONS.get(SYSTEM, ""))
EXE_NAME = "torrest{exe_extension}".format(exe_extension=EXECUTABLE_EXTENSIONS.get(SYSTEM, ""))
