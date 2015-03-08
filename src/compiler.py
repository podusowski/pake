import os
import subprocess
import marshal

import ui
import fsutils
import shell
import variable_deposit

# TODO: try to drop it
import parsing

class ConfigurationDeposit:
    def __init__(self, selected_configuration_name):
        self.selected_configuration_name = selected_configuration_name
        self.configurations = {}
        self.__create_default_configuration()

    def get_selected_configuration(self):
        return self.get_configuration(self.selected_configuration_name)

    def get_configuration(self, configuration_name):
        return self.configurations[configuration_name]

    def add_configuration(self, configuration):
        ui.debug("adding configuration: " + str(configuration))
        self.configurations[configuration.name] = configuration

    def __create_default_configuration(self):
        configuration = Configuration()
        self.add_configuration(configuration)

class Configuration:
    def __init__(self):
        self.name = "__default"
        self.compiler = [parsing.Token.make_literal("c++")]
        self.compiler_flags = [parsing.Token.make_literal("-I.")]
        self.linker_flags = [parsing.Token.make_literal("-L.")]
        self.application_suffix = [parsing.Token.make_literal("")]
        self.archiver = [parsing.Token.make_literal("ar")]
        self.export = []

    def __repr__(self):
        return self.name

class CxxToolchain:
    def __init__(self, configuration, variable_deposit, module_name, source_tree):
        self.configuration = configuration
        self.module_name = module_name
        self.source_tree = source_tree

        self.compiler_cmd = self.__simple_eval(configuration.compiler)
        self.compiler_flags = self.__simple_eval(configuration.compiler_flags)
        self.linker_flags = self.__simple_eval(configuration.linker_flags)
        self.archiver_cmd = self.__simple_eval(configuration.archiver)
        self.application_suffix = self.__simple_eval(configuration.application_suffix)

    def build_object(self, target_name, out_filename, in_filename, include_dirs, compiler_flags):
        ui.debug("building object " + out_filename)
        ui.push()
        prerequisites = self.__fetch_includes(target_name, in_filename, include_dirs, compiler_flags)
        prerequisites.append(in_filename)

        ui.debug("appending prerequisites from pake modules: " + str(self.source_tree.files))
        for module_filename in self.source_tree.files:
            prerequisites.append(module_filename)

        ui.debug("prerequisites: " + str(prerequisites))

        if fsutils.is_any_newer_than(prerequisites, out_filename):
            ui.step(self.compiler_cmd, in_filename)
            shell.execute("mkdir -p " + os.path.dirname(out_filename))
            shell.execute(self.compiler_cmd + " " + self.__prepare_compiler_flags(include_dirs, compiler_flags) + " -c -o " + out_filename + " " + in_filename)
        ui.pop()

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
                shell.execute(self.compiler_cmd + " " + self.linker_flags + " -o " + out_filename + " " + " ".join(in_filenames) + " " + self.__prepare_linker_flags(link_with) + " " + parameters)
            except Exception as e:
                ui.fatal("cannot link " + out_filename + ", reason: " + str(e))
        else:
            ui.bigstep("up to date", out_filename)

    def link_static_library(self, out_filename, in_filenames):
        ui.bigstep(self.archiver_cmd, out_filename)
        shell.execute(self.archiver_cmd + " -rcs " + out_filename + " " + " ".join(in_filenames))

    def object_filename(self, target_name, source_filename):
        return self.build_dir() + "/build." + target_name + "/" + source_filename + ".o"

    def static_library_filename(self, target_name):
        return self.build_dir() + "/lib" + target_name + ".a"

    def application_filename(self, target_name):
        return self.build_dir() + "/" + target_name + self.application_suffix

    def cache_directory(self, target_name):
        return self.build_dir() + "/build." + target_name + "/"

    def build_dir(self):
        return fsutils.build_dir(self.configuration.name)

    def __simple_eval(self, tokens):
        return " ".join(variable_deposit.eval(self.module_name, tokens))

    def __fetch_includes(self, target_name, in_filename, include_dirs, compiler_flags):
        ui.debug("getting includes for " + in_filename)
        ui.push()
        cache_file = self.cache_directory(target_name) + in_filename + ".includes"
        includes = None
        if os.path.exists(cache_file) and fsutils.is_newer_than(cache_file, in_filename):
            includes = marshal.load(open(cache_file))
        else:
            shell.execute("mkdir -p " + os.path.dirname(cache_file))
            includes = self.__scan_includes(in_filename, include_dirs, compiler_flags)
            marshal.dump(includes, open(cache_file, "w"))
        ui.pop()
        return includes

    def __scan_includes(self, in_filename, include_dirs, compiler_flags):
        ui.debug("scanning includes for " + in_filename)
        ret = []
        out = ""
        try:
            out = shell.execute(self.compiler_cmd + " " + self.__prepare_compiler_flags(include_dirs, compiler_flags) + " -M " + in_filename, capture_output = True).split()
        except:
            ui.fatal("can't finish request")

        for token in out[2:]:
            if token != "\\":
                ret.append(token)

        return ret

    def __prepare_linker_flags(self, link_with):
        ret = "-L " + self.build_dir() + " "
        for lib in link_with:
            ret = ret + " -l" + lib
        return ret

    def __prepare_compiler_flags(self, include_dirs, compiler_flags):
        ret = self.compiler_flags + " "
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


