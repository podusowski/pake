import os
import marshal

import ui
import fsutils
import shell
import configurations
import command_line


class Gnu:
    def build_object(self, target_name, out_filename, in_filename, include_dirs,
                     compiler_flags):
        ui.debug("building object " + out_filename)

        with ui.ident:
            prerequisites = self.__fetch_includes(target_name, in_filename,
                                                  include_dirs, compiler_flags)
            prerequisites.append(in_filename)

            ui.debug("appending prerequisites from pake modules: {!s}"
                     .format(fsutils.pake_files))
            for module_filename in fsutils.pake_files:
                prerequisites.append(module_filename)

            ui.debug("prerequisites: " + str(prerequisites))

            if fsutils.is_any_newer_than(prerequisites, out_filename):
                shell.execute("mkdir -p " + os.path.dirname(out_filename))

                cmd = configurations.compiler() + " " + self.__prepare_compiler_flags(include_dirs, compiler_flags) + " -c -o " + out_filename + " " + in_filename
                if command_line.args.verbose:
                    ui.step(configurations.compiler(), cmd)
                else:
                    ui.step(configurations.compiler(), in_filename)

                shell.execute(cmd)

    def link_application(self, out_filename, in_filenames, link_with, library_dirs):
        if fsutils.is_any_newer_than(in_filenames, out_filename) or self.__are_libs_newer_than_target(link_with, out_filename):
            ui.debug("linking application")
            ui.debug("  files: " + str(in_filenames))
            ui.debug("  with libs: " + str(link_with))
            ui.debug("  lib dirs: " + str(library_dirs))

            parameters = " ".join("-L " + lib_dir for lib_dir in library_dirs)

            ui.bigstep("linking", out_filename)
            try:
                shell.execute(" ".join([configurations.compiler(),
                                        configurations.linker_flags(),
                                        "-o", out_filename,
                                        " ".join(in_filenames),
                                        self.__prepare_linker_flags(link_with),
                                        parameters]))
            except Exception as e:
                ui.fatal("cannot link {}, reason: {!s}".format(out_filename, e))
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
        try:
            flags = self.__prepare_compiler_flags(include_dirs, compiler_flags)
            out = shell.execute(" ".join([configurations.compiler(), flags, "-M",
                                          in_filename]),
                                capture_output = True).split()
        except Exception as e:
            raise Exception("error while building dependency graph for"
                            "{!s}, {!s}".format(in_filename, e))

        return [token for token in out[2:] if not token == "\\"]

    def __prepare_linker_flags(self, link_with):
        libs_str = "".join(" -l" + lib for lib in link_with)
        return " ".join(["-L " + configurations.build_dir(), libs_str])

    def __prepare_compiler_flags(self, include_dirs, compiler_flags):
        return " ".join([configurations.compiler_flags(),
                         " ".join(compiler_flags),
                         self.__prepare_include_dirs_parameters(include_dirs)])

    def __prepare_include_dirs_parameters(self, include_dirs):
        ret = " ".join("-I" + include_dir for include_dir in include_dirs)
        ui.debug("include parameters: " + ret)
        return ret

    def __are_libs_newer_than_target(self, link_with, target):
        # check if the library is from our source tree
        files = (self.static_library_filename(lib) for lib in link_with)

        def is_newer_than_target(filename):
            if os.path.exists(filename):
                # TODO: proper appname
                return fsutils.is_newer_than(filename, target)

        return any(map(is_newer_than_target, files))
