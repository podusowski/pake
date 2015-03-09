import os
import marshal

import ui
import fsutils
import shell
import variables
import configurations

# TODO: try to drop it
import lexer

class Gnu:
    def build_object(self, target_name, out_filename, in_filename, include_dirs, compiler_flags):
        ui.debug("building object " + out_filename)

        with ui.ident:
            prerequisites = self.__fetch_includes(target_name, in_filename, include_dirs, compiler_flags)
            prerequisites.append(in_filename)

            ui.debug("appending prerequisites from pake modules: " + str(fsutils.pake_files))
            for module_filename in fsutils.pake_files:
                prerequisites.append(module_filename)

            ui.debug("prerequisites: " + str(prerequisites))

            if fsutils.is_any_newer_than(prerequisites, out_filename):
                ui.step(configurations.compiler(), in_filename)
                shell.execute("mkdir -p " + os.path.dirname(out_filename))
                shell.execute(configurations.compiler() + " " + self.__prepare_compiler_flags(include_dirs, compiler_flags) + " -c -o " + out_filename + " " + in_filename)

    def link_application(self, out_filename, in_filenames, link_with, library_dirs):
        if fsutils.is_any_newer_than(in_filenames, out_filename) or self.__are_libs_newer_than_target(link_with, out_filename):
            ui.debug("linking application")
            ui.debug("  files: " + str(in_filenames))
            ui.debug("  with libs: " + str(link_with))
            ui.debug("  lib dirs: " + str(library_dirs))

            parameters = ""
            for directory in library_dirs:
                parameters += "-L" + directory + " "

            ui.bigstep("linking", out_filename)
            try:
                shell.execute(configurations.compiler() + " " + configurations.linker_flags() + " -o " + out_filename + " " + " ".join(in_filenames) + " " + self.__prepare_linker_flags(link_with) + " " + parameters)
            except Exception as e:
                ui.fatal("cannot link " + out_filename + ", reason: " + str(e))
        else:
            ui.bigstep("up to date", out_filename)

    def link_static_library(self, out_filename, in_filenames):
        ui.bigstep(configurations.archiver(), out_filename)
        shell.execute(configurations.archiver() + " -rcs " + out_filename + " " + " ".join(in_filenames))

    def object_filename(self, target_name, source_filename):
        return configurations.build_dir() + "/build." + target_name + "/" + source_filename + ".o"

    def static_library_filename(self, target_name):
        return configurations.build_dir() + "/lib" + target_name + ".a"

    def application_filename(self, target_name):
        return configurations.build_dir() + "/" + target_name + configurations.application_suffix()

    def cache_directory(self, target_name):
        return configurations.build_dir() + "/build." + target_name + "/"

    def build_dir(self):
        return configurations.build_dir()

    def __fetch_includes(self, target_name, in_filename, include_dirs, compiler_flags):
        ui.debug("getting includes for " + in_filename)

        with ui.ident:
            cache_file = self.cache_directory(target_name) + in_filename + ".includes"
            includes = None
            if os.path.exists(cache_file) and fsutils.is_newer_than(cache_file, in_filename):
                includes = marshal.load(open(cache_file))
            else:
                shell.execute("mkdir -p " + os.path.dirname(cache_file))
                includes = self.__scan_includes(in_filename, include_dirs, compiler_flags)
                marshal.dump(includes, open(cache_file, "w"))

        return includes

    def __scan_includes(self, in_filename, include_dirs, compiler_flags):
        ui.debug("scanning includes for " + in_filename)
        ret = []
        out = ""
        try:
            out = shell.execute(configurations.compiler() + " " + self.__prepare_compiler_flags(include_dirs, compiler_flags) + " -M " + in_filename, capture_output = True).split()
        except:
            ui.fatal("can't finish request")

        for token in out[2:]:
            if token != "\\":
                ret.append(token)

        return ret

    def __prepare_linker_flags(self, link_with):
        ret = "-L " + configurations.build_dir() + " "
        for lib in link_with:
            ret = ret + " -l" + lib
        return ret

    def __prepare_compiler_flags(self, include_dirs, compiler_flags):
        ret = configurations.compiler_flags() + " "
        for flag in compiler_flags:
            ret += flag + " "
        ret += self.__prepare_include_dirs_parameters(include_dirs) + " "
        return ret

    def __prepare_include_dirs_parameters(self, include_dirs):
        ret = ""
        for include_dir in include_dirs:
            ret += "-I" + include_dir + " "

        ui.debug("include parameters: " + ret)

        return ret

    def __are_libs_newer_than_target(self, link_with, target):
        # check if the library is from our source tree
        for lib in link_with:
            filename = self.static_library_filename(lib)
            if os.path.exists(filename):
                # TODO: proper appname
                if fsutils.is_newer_than(filename, target):
                    return True
        return False


