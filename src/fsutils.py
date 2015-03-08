import os
import ui

BUILD_ROOT = os.path.normpath(os.getcwd() + "/__build")

def build_dir(configuration_name):
    return os.path.normpath(BUILD_ROOT + "/" + configuration_name)

def is_newer_than(prerequisite, target):
    if os.path.exists(target):
        ret = get_mtime(prerequisite) > get_mtime(target)
        ui.debug("is " + prerequisite + " newer than " + target + " = " + str(ret))
        return ret
    else:
        ui.debug(target + " doesn't exist, treating like older")
        return True

def is_any_newer_than(prerequisites, target):
    for prerequisite in prerequisites:
        if is_newer_than(prerequisite, target):
            return True
    return False

def get_mtime(filename):
    return os.path.getmtime(filename)

class SourceTree:
    def __init__(self):
        self.files = self.__find_pake_files()

    def __find_pake_files(self, path = os.getcwd()):
        ret = []
        for (dirpath, dirnames, filenames) in os.walk(path):
            for f in filenames:
                if not dirpath.startswith(BUILD_ROOT):
                    filename = dirpath + "/" + f
                    (base, ext) = os.path.splitext(filename)
                    if ext == ".pake":
                        ret.append(filename)
        return ret

def _find_pake_files():
    tree = SourceTree()
    return tree.files

pake_files = _find_pake_files()

