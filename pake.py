#!/usr/bin/env python

import os
import sys
import tempfile
import stat
import subprocess
import argparse
import marshal
import shutil


"""
    utilities
"""

class FsUtils:
    BUILD_ROOT = os.path.normpath(os.getcwd() + "/__build")

    @staticmethod
    def build_dir(configuration_name):
        return os.path.normpath(FsUtils.BUILD_ROOT + "/" + configuration_name)

    @staticmethod
    def is_newer_than(prerequisite, target):
        if os.path.exists(target):
            ret = FsUtils.get_mtime(prerequisite) > FsUtils.get_mtime(target)
            Ui.debug("is " + prerequisite + " newer than " + target + " = " + str(ret))
            return ret
        else:
            Ui.debug(target + " doesn't exist, treating like older")
            return True

    @staticmethod
    def is_any_newer_than(prerequisites, target):
        for prerequisite in prerequisites:
            if FsUtils.is_newer_than(prerequisite, target):
                return True
        return False

    @staticmethod
    def get_mtime(filename):
        return os.path.getmtime(filename)

def execute(command, capture_output = False):
    out = ''
    try:
        if capture_output:
            out = subprocess.check_output(command, shell=True)
        else:
            subprocess.check_call(command, shell=True)
    except subprocess.CalledProcessError:
        Ui.fatal("command did not finish successfully: " + command)

    Ui.debug("command completed: " + command)
    return out


class Ui:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    GRAY = '\033[90m'
    RED = '\033[31m'
    BOLD_RED = '\033[1;31m'
    BOLD_BLUE = "\033[34;1m"

    log_depth = 0

    @staticmethod
    def push():
        Ui.log_depth += 1

    @staticmethod
    def pop():
        Ui.log_depth -= 1

    @staticmethod
    def print_depth_prefix():
        for i in range(Ui.log_depth):
            sys.stdout.write("    ")

    @staticmethod
    def info(message):
        print(message)
        sys.stdout.flush()

    @staticmethod
    def step(tool, parameter):
        if sys.stdout.isatty():
            print(Ui.BOLD + tool + Ui.RESET + " " + parameter)
        else:
            print(tool + " " + parameter)
        sys.stdout.flush()

    @staticmethod
    def bigstep(tool, parameter):
        if sys.stdout.isatty():
            print(Ui.BOLD_BLUE + tool + Ui.RESET + " " + parameter)
        else:
            print(tool + " " + parameter)
        sys.stdout.flush()

    @staticmethod
    def fatal(message):
        if sys.stdout.isatty():
            print(Ui.BOLD_RED + "fatal: " + Ui.RESET + message)
        else:
            print("fatal: " + message)
        sys.stdout.flush()
        sys.exit(1)

    @staticmethod
    def parse_error(token = None, msg = None):
        if token != None:
            s = token.location_str()
            if msg != None:
                s += ": " + msg
            else:
                s += ": unexpected " + str(token)
            Ui.fatal(s)
        else:
            Ui.fatal(msg)

    @staticmethod
    def debug(s, env = None):
        if "DEBUG" in os.environ:
            if env == None or env in os.environ:
                Ui.print_depth_prefix()
                print(Ui.GRAY + s + Ui.RESET)

"""
    C++ compiler support
"""

class CxxToolchain:
    def __init__(self, configuration, variable_deposit, module_name, source_tree):
        self.configuration = configuration
        self.variable_deposit = variable_deposit
        self.module_name = module_name
        self.source_tree = source_tree

        self.compiler_cmd = self.__simple_eval(configuration.compiler)
        self.compiler_flags = self.__simple_eval(configuration.compiler_flags)
        self.linker_flags = self.__simple_eval(configuration.linker_flags)
        self.archiver_cmd = self.__simple_eval(configuration.archiver)
        self.application_suffix = self.__simple_eval(configuration.application_suffix)

    def build_object(self, target_name, out_filename, in_filename, include_dirs, compiler_flags):
        Ui.debug("building object " + out_filename)
        Ui.push()
        prerequisites = self.__fetch_includes(target_name, in_filename, include_dirs, compiler_flags)
        prerequisites.append(in_filename)

        Ui.debug("appending prerequisites from pake modules: " + str(self.source_tree.files))
        for module_filename in self.source_tree.files:
            prerequisites.append(module_filename)

        Ui.debug("prerequisites: " + str(prerequisites))

        if FsUtils.is_any_newer_than(prerequisites, out_filename):
            Ui.step(self.compiler_cmd, in_filename)
            execute("mkdir -p " + os.path.dirname(out_filename))
            execute(self.compiler_cmd + " " + self.__prepare_compiler_flags(include_dirs, compiler_flags) + " -c -o " + out_filename + " " + in_filename)
        Ui.pop()

    def link_application(self, out_filename, in_filenames, link_with, library_dirs):
        if FsUtils.is_any_newer_than(in_filenames, out_filename) or self.__are_libs_newer_than_target(link_with, out_filename):
            Ui.debug("linking application")
            Ui.debug("  files: " + str(in_filenames))
            Ui.debug("  with libs: " + str(link_with))
            Ui.debug("  lib dirs: " + str(library_dirs))

            parameters = ""
            for directory in library_dirs:
                parameters += "-L" + directory + " "

            Ui.bigstep("linking", out_filename)
            execute(self.compiler_cmd + " " + self.linker_flags + " -o " + out_filename + " " + " ".join(in_filenames) + " " + self.__libs_arguments(link_with) + " " + parameters)
        else:
            Ui.bigstep("up to date", out_filename)

    def link_static_library(self, out_filename, in_filenames):
        Ui.bigstep(self.archiver_cmd, out_filename)
        execute(self.archiver_cmd + " -rcs " + out_filename + " " + " ".join(in_filenames))

    def object_filename(self, target_name, source_filename):
        return self.build_dir() + "/build." + target_name + "/" + source_filename + ".o"

    def static_library_filename(self, target_name):
        return self.build_dir() + "/lib" + target_name + ".a"

    def application_filename(self, target_name):
        return self.build_dir() + "/" + target_name + self.application_suffix

    def cache_directory(self, target_name):
        return self.build_dir() + "/build." + target_name + "/"

    def build_dir(self):
        return FsUtils.build_dir(self.configuration.name)

    def __simple_eval(self, tokens):
        return " ".join(self.variable_deposit.eval(self.module_name, tokens))

    def __fetch_includes(self, target_name, in_filename, include_dirs, compiler_flags):
        Ui.debug("getting includes for " + in_filename)
        Ui.push()
        cache_file = self.cache_directory(target_name) + in_filename + ".includes"
        includes = None
        if os.path.exists(cache_file) and FsUtils.is_newer_than(cache_file, in_filename):
            includes = marshal.load(open(cache_file))
        else:
            execute("mkdir -p " + os.path.dirname(cache_file))
            includes = self.__scan_includes(in_filename, include_dirs, compiler_flags)
            marshal.dump(includes, open(cache_file, "w"))
        Ui.pop()
        return includes

    def __scan_includes(self, in_filename, include_dirs, compiler_flags):
        Ui.debug("scanning includes for " + in_filename)
        ret = []
        out = execute(self.compiler_cmd + " " + self.__prepare_compiler_flags(include_dirs, compiler_flags) + " -M " + in_filename, capture_output = True).split()
        for token in out[2:]:
            if token != "\\":
                ret.append(token)

        # in standard c++ code, standard and library includes will be first
        ret.reverse()
        return ret

    def __libs_arguments(self, link_with):
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

        Ui.debug("include parameters: " + ret)

        return ret

    def __are_libs_newer_than_target(self, link_with, target):
        # check if the library is from our source tree
        for lib in link_with:
            filename = self.static_library_filename(lib)
            if os.path.exists(filename):
                # TODO: proper appname
                if FsUtils.is_newer_than(filename, target):
                    return True
        return False

"""
    targets
"""

class CommonTargetParameters:
    def __init__(self, variable_deposit, root_path, module_name, name):
        assert isinstance(variable_deposit, VariableDeposit)
        assert isinstance(module_name, str)
        assert isinstance(name, str)

        self.variable_deposit = variable_deposit
        self.root_path = root_path
        self.module_name = module_name
        self.name = name
        self.artefacts = []
        self.prerequisites = []
        self.depends_on = []
        self.run_before = []
        self.run_after = []
        self.resources = []
        self.visible_in = []

class CxxParameters:
    def __init__(self):
        self.sources = []
        self.include_dirs = []
        self.compiler_flags = []
        self.built_targets = []

class TargetDeposit:
    def __init__(self, variable_deposit, configuration_deposit, source_tree):
        self.variable_deposit = variable_deposit
        self.configuration_deposit = configuration_deposit
        self.source_tree = source_tree
        self.targets = {}
        self.built_targets = []

    def __repr__(self):
        s = ''
        for target in self.targets:
            s += " * " + target + "\n"
        return s

    def add_target(self, target):
        self.targets[target.common_parameters.name] = target

    def build(self, name):
        configuration = self.configuration_deposit.get_selected_configuration()

        execute("mkdir -p " + FsUtils.build_dir(configuration.name))

        Ui.debug("building " + name + " with configuration " + str(configuration))
        Ui.push()

        if name in self.built_targets:
            Ui.debug(name + " already build, skipping")
            return
        else:
            self.built_targets.append(name)

        if not name in self.targets:
            Ui.fatal("target " + name + " not found")

        target = self.targets[name]

        if not target.is_visible(configuration):
            Ui.fatal("target " + name + " is not visible in " + str(configuration))

        evalueated_depends_on = self.variable_deposit.eval(
            target.common_parameters.module_name,
            target.common_parameters.depends_on)

        for dependency in evalueated_depends_on:
            Ui.debug(name + " depends on " + dependency)
            self.build(dependency)

        toolchain = CxxToolchain(
            configuration,
            self.variable_deposit,
            target.common_parameters.name,
            self.source_tree)

        target.before()
        target.build(toolchain)
        target.after()
        target.copy_resources(toolchain)

        Ui.pop()

    def build_all(self):
        Ui.bigstep("building all targets", " ".join(self.targets))

        configuration = self.configuration_deposit.get_selected_configuration()

        for name in self.targets:
            target = self.targets[name]
            if target.is_visible(configuration):
                self.build(name)
            else:
                Ui.bigstep("skip", name)

class Target:
    def __init__(self, common_parameters):
        self.common_parameters = common_parameters

    def __repr__(self):
        return self.common_parameters.name

    def before(self):
        self.__try_run(self.common_parameters.run_before)

    def after(self):
        self.__try_run(self.common_parameters.run_after)

    def copy_resources(self, toolchain):
        root_dir = os.getcwd()
        os.chdir(self.common_parameters.root_path)

        resources = self.eval(self.common_parameters.resources)
        for resource in resources:
            Ui.step("copy", resource)
            shutil.copy(resource, toolchain.build_dir() + "/")

        os.chdir(root_dir)

    def is_visible(self, configuration):
        evaluated_visible_in = self.eval(self.common_parameters.visible_in)
        if len(evaluated_visible_in) > 0:
            for visible_in in evaluated_visible_in:
                if visible_in == configuration.name:
                    return True
            return False
        else:
            return True

    def __try_run(self, cmds):
        root_dir = os.getcwd()
        os.chdir(self.common_parameters.root_path)

        evaluated_artefacts = self.eval(self.common_parameters.artefacts)
        evaluated_prerequisites = self.eval(self.common_parameters.prerequisites)

        should_run = True
        if len(evaluated_prerequisites) > 0 and len(evaluated_artefacts) > 0:
            should_run = False
            Ui.debug("checking prerequisites (" + str(evaluated_prerequisites) + ") for making " + str(evaluated_artefacts))
            for artefact in evaluated_artefacts:
                Ui.debug("  " + artefact)
                if FsUtils.is_any_newer_than(evaluated_prerequisites, artefact):
                    Ui.debug("going on because " + str(artefact) + " needs to be rebuilt")
                    should_run = True
                    break

        if should_run:
            self.common_parameters.variable_deposit.pollute_environment(self.common_parameters.module_name)

            evaluated_cmds = self.eval(cmds)

            for cmd in evaluated_cmds:
                Ui.debug("running " + str(cmd))
                execute(cmd)

        os.chdir(root_dir)

    def eval(self, variable):
        return self.common_parameters.variable_deposit.eval(
            self.common_parameters.module_name,
            variable)

class Phony(Target):
    def __init__(self, common_parameters):
        Target.__init__(self, common_parameters)

    def build(self, configuration):
        Ui.debug("phony build")

class CompileableTarget(Target):
    def __init__(self, common_parameters, cxx_parameters):
        Target.__init__(self, common_parameters)

        self.common_parameters = common_parameters
        self.cxx_parameters = cxx_parameters

    def build_objects(self, toolchain):
        object_files = []
        evaluated_sources = self.eval(self.cxx_parameters.sources)
        evaluated_include_dirs = self.eval(self.cxx_parameters.include_dirs)
        evaluated_compiler_flags = self.eval(self.cxx_parameters.compiler_flags)

        Ui.debug("building objects from " + str(evaluated_sources))
        Ui.push()

        for source in evaluated_sources:
            object_file = toolchain.object_filename(self.common_parameters.name, source)
            object_files.append(object_file)
            toolchain.build_object(self.common_parameters.name, object_file, source, evaluated_include_dirs, evaluated_compiler_flags)

        Ui.pop()

        return object_files

class Application(CompileableTarget):
    def __init__(self, common_parameters, cxx_parameters, link_with, library_dirs):
        CompileableTarget.__init__(self, common_parameters, cxx_parameters)

        self.link_with = link_with
        self.library_dirs = library_dirs

    def build(self, toolchain):
        root_dir = os.getcwd()
        os.chdir(self.common_parameters.root_path)

        object_files = self.build_objects(toolchain)

        evaluated_link_with = self.eval(self.link_with)
        evaluated_library_dirs = self.eval(self.library_dirs)

        toolchain.link_application(
            toolchain.application_filename(self.common_parameters.name),
            object_files,
            evaluated_link_with,
            evaluated_library_dirs)

        os.chdir(root_dir)

class StaticLibrary(CompileableTarget):
    def __init__(self, common_parameters, cxx_parameters):
        CompileableTarget.__init__(self, common_parameters, cxx_parameters)

    def build(self, toolchain):
        root_dir = os.getcwd()
        os.chdir(self.common_parameters.root_path)

        object_files = self.build_objects(toolchain)

        artefact = toolchain.static_library_filename(self.common_parameters.name)

        if FsUtils.is_any_newer_than(object_files, artefact):
            toolchain.link_static_library(artefact, object_files)
        else:
            Ui.bigstep("up to date", artefact)

        os.chdir(root_dir)

"""
    parser
"""

class VariableDeposit:
    def __init__(self):
        self.modules = {}

    def export_special_variables(self, configuration):
        Ui.debug("exporting special variables")
        Ui.push()

        self.add_empty("__configuration", "$__null")
        self.add("__configuration", "$__name", Token.make_literal(configuration.name))
        for (value, name) in configuration.export:
            self.add("__configuration", name.content, value)

        for module in self.modules:
            self.add(module, "$__build", Token(Token.LITERAL, FsUtils.build_dir(configuration.name)))

        Ui.pop()

    def pollute_environment(self, current_module):
        Ui.debug("polluting environment")
        Ui.push()
        for module in self.modules:
            for (name, variable) in self.modules[module].iteritems():
                evaluated = self.eval(module, variable)
                env_name = module + "_" + name[1:]
                os.environ[env_name] = " ".join(evaluated)
                Ui.debug("  " + env_name + ": " + str(evaluated))
                if module == current_module:
                    env_short_name = name[1:]
                    os.environ[env_short_name] = " ".join(evaluated)
                    Ui.debug("  " + env_short_name + ": " + str(evaluated))
        Ui.pop()

    def eval(self, current_module, l):
        Ui.debug("evaluating " + str(l) + " in context of module " + current_module)
        Ui.push()

        ret = []
        for token in l:
            if token.is_a(Token.LITERAL):
                content = self.__eval_literal(current_module, token.content)
                Ui.debug("  " + token.content + " = " + content)
                ret.append(content)
            elif token.is_a(Token.VARIABLE):
                parts = token.content.split(".")

                Ui.debug("dereferencing " + str(parts))

                module = ''
                name = ''
                if len(parts) == 1:
                    module = current_module
                    name = parts[0]
                elif len(parts) == 2:
                    module = parts[0][1:] # lose the $
                    name = "$" + parts[1]

                if not module in self.modules:
                    Ui.parse_error(msg="no such module: " + module)

                # TODO: make some comment about __configuration variables
                if not name in self.modules[module]:
                    Ui.fatal("dereferenced " + name + " but it doesn't exists in module " + module)

                for value in self.modules[module][name]:
                    if value.is_a(Token.VARIABLE):
                        re = self.eval(module, [value])
                        for v in re: ret.append(v)
                    else:
                        content = self.__eval_literal(module, value.content)
                        ret.append(content)
                        Ui.debug("    = " + str(content))
            else:
                Ui.parse_error(token)

        Ui.debug(" = " + str(ret))
        Ui.pop()
        return ret

    def __eval_literal(self, current_module, s):
        Ui.debug("evaluating literal: " + s)
        Ui.push()
        ret = ""

        STATE_READING = 1
        STATE_WAITING_FOR_PARENTHESIS = 2
        STATE_READING_NAME = 3

        variable_name = '$'
        state = STATE_READING

        for c in s:
            if state == STATE_READING:
                if c == "$":
                    state = STATE_WAITING_FOR_PARENTHESIS
                else:
                    ret += c
            elif state == STATE_WAITING_FOR_PARENTHESIS:
                if c == "{":
                    state = STATE_READING_NAME
                else:
                    Ui.parse_error(msg="expecting { after $")
            elif state == STATE_READING_NAME:
                if c == "}":
                    Ui.debug("variable: " + variable_name)
                    evaluated_variable = self.eval(current_module, [Token(Token.VARIABLE, variable_name)])
                    ret += " ".join(evaluated_variable)
                    variable_name = '$'
                    state = STATE_READING
                else:
                    variable_name += c
            elif state == STATE_READING_NAME:
                variable_name = variable_name + c

        Ui.pop()
        return ret

    def add_empty(self, module_name, name):
        Ui.debug("adding empty variable in module " + module_name + " called " + name)

        if not module_name in self.modules:
            self.modules[module_name] = {}

        self.modules[module_name][name] = []


    def add(self, module_name, name, value):
        Ui.debug("adding variable in module " + module_name + " called " + name + " with value of " + str(value))

        if not module_name in self.modules:
            self.modules[module_name] = {}

        self.modules[module_name][name] = [value]

    def append(self, module_name, name, value):
        Ui.debug("appending variable in module " + module_name + " called " + name + " with value of " + str(value))

        if not module_name in self.modules:
            self.modules[module_name] = {}

        if not name in self.modules[module_name]:
            self.modules[module_name][name] = []

        self.modules[module_name][name].append(value)
        Ui.debug("  new value: " + str(self.modules[module_name][name]))

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
        Ui.debug("adding configuration: " + str(configuration))
        self.configurations[configuration.name] = configuration

    def __create_default_configuration(self):
        configuration = Configuration()
        self.add_configuration(configuration)

class Configuration:
    def __init__(self):
        self.name = "__default"
        self.compiler = [Token.make_literal("c++")]
        self.compiler_flags = [Token.make_literal("-I.")]
        self.linker_flags = [Token.make_literal("-L.")]
        self.application_suffix = [Token.make_literal("")]
        self.archiver = [Token.make_literal("ar")]
        self.export = []

    def __repr__(self):
        return self.name

class Module:
    def __init__(self, variable_deposit, configuration_deposit, target_deposit, filename):
        assert isinstance(variable_deposit, VariableDeposit)
        assert isinstance(filename, str)

        Ui.debug("parsing " + filename)
        Ui.push()

        self.variable_deposit = variable_deposit
        self.configuration_deposit = configuration_deposit
        self.target_deposit = target_deposit
        self.filename = filename
        self.name = self.__get_module_name(filename)
        self.lines = []
        self.targets = []
        self.base_dir = os.path.dirname(filename)

        tokenizer = Tokenizer(filename)
        self.tokens = tokenizer.tokens

        self.__parse()

        self.variable_deposit.add(
            self.name,
            "$__path",
            Token.make_literal(os.path.dirname(self.filename)))

        self.variable_deposit.add_empty(
            self.name,
            "$__null")

        Ui.pop()

    def __get_module_name(self, filename):
        base = os.path.basename(filename)
        (root, ext) = os.path.splitext(base)
        return root

    def __add_target(self, target):
        Ui.debug("adding target: " + str(target))
        self.targets.append(target)
        self.target_deposit.add_target(target)

    def __parse_set_or_append(self, it, append):
        token = it.next()
        if token.is_a(Token.VARIABLE):
            variable_name = token.content
        else:
            Ui.parse_error(token)

        second_add = False
        while True:
            token = it.next()
            if token.is_a(Token.LITERAL) or token.is_a(Token.VARIABLE):
                if append or second_add:
                    self.variable_deposit.append(self.name, variable_name, token)
                else:
                    self.variable_deposit.add(self.name, variable_name, token)
                    second_add = True

            elif token.is_a(Token.NEWLINE):
                break
            else:
                Ui.parse_error(token)

    # (something1 something2)
    def __parse_list(self, it):
        ret = []
        token = it.next()
        if token.is_a(Token.OPEN_PARENTHESIS):

            while True:
                token = it.next()
                if token.is_a(Token.LITERAL):
                    ret.append(token)
                elif token.is_a(Token.VARIABLE):
                    ret.append(token)
                elif token.is_a(Token.CLOSE_PARENTHESIS):
                    break
                else:
                    Ui.parse_error(token)
        else:
            Ui.parse_error(token)

        return ret

    # ($var1:$var2 something4:$var1)
    def __parse_colon_list(self, it):
        ret = []
        token = it.next()
        if token.is_a(Token.OPEN_PARENTHESIS):

            while True:
                token = it.next()

                first = None
                second = None

                if token.is_a(Token.LITERAL) or token.is_a(Token.VARIABLE):
                    first = token
                    token = it.next()
                    if token.is_a(Token.COLON):
                        token = it.next()
                        if token.is_a(Token.VARIABLE):
                            second = token
                            ret.append((first, second))
                        else:
                            Ui.parse_error(token, msg="expected variable")
                    else:
                        Ui.parse_error(token, msg="expected colon")
                elif token.is_a(Token.CLOSE_PARENTHESIS):
                    break
                else:
                    Ui.parse_error(token)
        else:
            Ui.parse_error(token)

        Ui.debug("colon list: " + str(ret))
        return ret

    def __try_parse_target_common_parameters(self, common_parameters, token, it):
        if token.content == "depends_on":
            common_parameters.depends_on = self.__parse_list(it)
            return True
        elif token.content == "run_before":
            common_parameters.run_before = self.__parse_list(it)
            return True
        elif token.content == "run_after":
            common_parameters.run_after = self.__parse_list(it)
            return True
        elif token.content == "resources":
            common_parameters.resources = self.__parse_list(it)
            return True
        elif token.content == "visible_in":
            common_parameters.visible_in = self.__parse_list(it)
            return True

        return False

    def __try_parse_cxx_parameters(self, cxx_parameters, token, it):
        if token.content == "sources":
            cxx_parameters.sources = self.__parse_list(it)
            return True
        elif token.content == "include_dirs":
            cxx_parameters.include_dirs = self.__parse_list(it)
            return True
        elif token.content == "compiler_flags":
            cxx_parameters.compiler_flags = self.__parse_list(it)
            return True

        return False

    def __parse_application_target(self, target_name, it):
        link_with = []
        library_dirs = []

        common_parameters = CommonTargetParameters(
            self.variable_deposit,
            os.path.dirname(self.filename),
            self.name,
            target_name)

        cxx_parameters = CxxParameters()

        while True:
            token = it.next()
            if token.is_a(Token.LITERAL):
                if self.__try_parse_target_common_parameters(common_parameters, token, it): pass
                elif self.__try_parse_cxx_parameters(cxx_parameters, token, it): pass
                elif token.content == "link_with": link_with = self.__parse_list(it)
                elif token.content == "library_dirs": library_dirs = self.__parse_list(it)
                else: Ui.parse_error(token)
            elif token.is_a(Token.NEWLINE):
                break
            else:
                Ui.parse_error(token)

        target = Application(common_parameters, cxx_parameters, link_with, library_dirs)
        self.__add_target(target)

    def __parse_static_library(self, target_name, it):
        common_parameters = CommonTargetParameters(
            self.variable_deposit,
            os.path.dirname(self.filename),
            self.name,
            target_name)

        cxx_parameters = CxxParameters()

        while True:
            token = it.next()
            if token.is_a(Token.LITERAL):
                if self.__try_parse_target_common_parameters(common_parameters, token, it): pass
                elif self.__try_parse_cxx_parameters(cxx_parameters, token, it): pass
                else: Ui.parse_error(token)
            elif token.is_a(Token.NEWLINE):
                break
            else:
                Ui.parse_error(token)

        target = StaticLibrary(common_parameters, cxx_parameters)
        self.__add_target(target)

    def __parse_phony(self, target_name, it):
        common_parameters = CommonTargetParameters(
            self.variable_deposit,
            os.path.dirname(self.filename),
            self.name,
            target_name)

        cxx_parameters = CxxParameters()

        while True:
            token = it.next()
            if token.is_a(Token.LITERAL):
                if self.__try_parse_target_common_parameters(common_parameters, token, it): pass
                elif token.content == "artefacts": common_parameters.artefacts = self.__parse_list(it)
                elif token.content == "prerequisites": common_parameters.prerequisites = self.__parse_list(it)
                else: Ui.parse_error(token)

            elif token.is_a(Token.NEWLINE):
                break
            else:
                Ui.parse_error(token)

        target = Phony(common_parameters)
        self.__add_target(target)

    def __parse_target(self, it):
        token = it.next()
        if token.is_a(Token.LITERAL):
            target_type = token.content

            token = it.next()
            if token.is_a(Token.LITERAL):
                target_name = token.content
            else:
                Ui.parse_error(token)
        else:
            Ui.parse_error(token)

        if target_type == "application":       self.__parse_application_target(target_name, it)
        elif target_type == "static_library":  self.__parse_static_library(target_name, it)
        elif target_type == "phony":           self.__parse_phony(target_name, it)
        else: Ui.parse_error(token, msg="unknown target type: " + target_type)

    def __parse_configuration(self, it):
        configuration = Configuration()

        # name
        token = it.next()
        if token.is_a(Token.LITERAL):
            configuration.name = token.content
        else:
            Ui.parse_error(token)

        while True:
            token = it.next()
            if token.is_a(Token.LITERAL):
                if token.content == "compiler": configuration.compiler = self.__parse_list(it)
                elif token.content == "archiver": configuration.archiver = self.__parse_list(it)
                elif token.content == "application_suffix": configuration.application_suffix = self.__parse_list(it)
                elif token.content == "compiler_flags": configuration.compiler_flags = self.__parse_list(it)
                elif token.content == "linker_flags": configuration.linker_flags = self.__parse_list(it)
                elif token.content == "export": configuration.export = self.__parse_colon_list(it)
                else: Ui.parse_error(token)

            elif token.is_a(Token.NEWLINE):
                break
            else:
                Ui.parse_error(token)

        Ui.debug("configuration parsed:" + str(configuration))
        self.configuration_deposit.add_configuration(configuration)

    def __parse_directive(self, it):
        while True:
            token = it.next()

            if token.is_a(Token.LITERAL):
                if token.content == "set" or token.content == "append": self.__parse_set_or_append(it, token.content == "append")
                elif token.content == "target":                    self.__parse_target(it)
                elif token.content == "configuration":             self.__parse_configuration(it)
                else: Ui.parse_error(token, msg="expected directive")

            elif token.is_a(Token.NEWLINE):
                continue
            else:
                return False

    def __parse(self):
        it = iter(self.tokens)

        try:
            if not self.__parse_directive(it):
                Ui.parse_error(msg="unknown :(")
        except StopIteration:
            Ui.debug("eof")

class FileReader:
    def __init__(self, filename):
        self.line_number = 1

        f = open(filename, "r")
        self.position = 0
        self.buf = f.read()
        f.close()

    def value(self):
        if self.eof():
            Ui.debug("Read out of range: " + str(self.position), "TOKENIZER")
            raise Exception("eof")

        Ui.debug("read: " + str(self.buf[self.position]), "TOKENIZER")
        return str(self.buf[self.position])

    def rewind(self, value = 1):
        if value > 0:
            for i in xrange(value):
                self.position += 1
                if not self.eof() and self.buf[self.position] == '\n':
                    self.line_number += 1
        elif value < 0:
            for i in xrange(-value):
                self.position -= 1
                if not self.eof() and self.buf[self.position] == '\n':
                    self.line_number -= 1
        else:
            raise Exception("rewind by 0")

    def seek(self, value):
        self.position = value

    def tell(self):
        return self.position

    def eof(self):
        return self.position >= len(self.buf) or self.position < 0

class Token:
    OPEN_PARENTHESIS = 1
    CLOSE_PARENTHESIS = 2
    LITERAL = 3
    VARIABLE = 4
    NEWLINE = 5
    MULTILINE_LITERAL = 6
    COLON = 7

    @staticmethod
    def make_literal(content):
        return Token(Token.LITERAL, content)

    def __init__(self, token_type, content, filename = None, line = None, col = None):
        self.token_type = token_type
        self.content = content

        self.filename = filename
        self.line = line
        self.col = col

    def __repr__(self):
        if self.is_a(Token.LITERAL):
            return "literal: " + self.content
        elif self.is_a(Token.VARIABLE):
            return "variable: " + self.content
        else:
            return self.content

    def location_str(self):
        return str(self.filename) + ":" + str(self.line) + ":" + str(self.col)

    def is_a(self, token_type):
        return self.token_type == token_type

class Tokenizer:
    def __init__(self, filename):
        self.filename = filename
        buf = FileReader(filename)
        self.tokens = []
        self.__tokenize(buf)
        Ui.debug("tokens: " + str(self.tokens))

    def __is_valid_identifier_char(self, char):
        return char.isalnum() or char in './$_-=+'

    def __try_add_variable_or_literal(self, token_type, data, line):
        if len(data) > 0:
            self.__add_token(token_type, data, line)
        return ""

    def __add_token(self, token_type, content, line = None):
        token = Token(token_type, content, self.filename, line)
        self.tokens.append(token)

    def __try_to_read_token(self, buf, what):
        old_position = buf.tell()
        what_position = 0

        while not buf.eof() and what_position < len(what):
            what_char = what[what_position]
            char = buf.value()

            if what_char != char:
                break
            else:
                if what_position == len(what) - 1:
                    buf.rewind()
                    return True

            buf.rewind()
            what_position += 1

        buf.seek(old_position)
        return False

    def __try_tokenize_multiline_literal(self, buf):
        pos = buf.tell()
        data = ''

        if self.__try_to_read_token(buf, '"""'):
            Ui.debug("reading multine", "TOKENIZER")
            while True:
                if buf.eof():
                    raise Exception("parse error")

                char = buf.value()

                if self.__try_to_read_token(buf, '"""'):
                    self.__add_token(Token.MULTILINE_LITERAL, data, buf.line_number)
                    return True
                else:
                    data = data + char

                buf.rewind()
        else:
            Ui.debug("no multine", "TOKENIZER")
            buf.seek(pos)

        return False

    def __try_tokenize_comment(self, buf):
        if buf.eof():
            return False

        if buf.value() == '#':
            while not buf.eof() and buf.value() != '\n':
                buf.rewind()
            return True
        return False

    def __try_tokenize_slash_newline(self, buf):
        if buf.eof():
            return False

        pos = buf.tell()

        char = buf.value()
        if char == "\\":
            buf.rewind()
            char = buf.value()
            if char == "\n":
                buf.rewind()
                return True
        buf.seek(pos)

        return False

    def __try_tokenize_simple_chars(self, buf):
        if buf.eof():
            return False

        char = buf.value()

        if char == '\n':
            self.__add_token(Token.NEWLINE, "<new-line>", buf.line_number)
            buf.rewind()
            return True
        elif char == '(':
            self.__add_token(Token.OPEN_PARENTHESIS, "(", buf.line_number)
            buf.rewind()
            return True
        elif char == ')':
            self.__add_token(Token.CLOSE_PARENTHESIS, ")", buf.line_number)
            buf.rewind()
            return True
        elif char == ':':
            self.__add_token(Token.COLON, ":", buf.line_number)
            buf.rewind()
            return True

        return False

    def __try_tokenize_variable_or_literal(self, buf):
        if buf.eof() or not self.__is_valid_identifier_char(buf.value()):
            return False

        if buf.value() == '$':  token_type = Token.VARIABLE
        else:                   token_type = Token.LITERAL

        data = ''
        while not buf.eof():
            c = buf.value()
            if self.__is_valid_identifier_char(c):
                data = data + c
                buf.rewind()
            else:
                break

        self.__try_add_variable_or_literal(token_type, data, buf.line_number)

        return True

    def __try_tokenize_quoted_literal(self, buf):
        pos = buf.tell()
        data = ''

        if self.__try_to_read_token(buf, '"'):
           while True:
                if buf.eof():
                    raise Exception("parse error")

                if self.__try_to_read_token(buf, '"'):
                    self.__add_token(Token.LITERAL, data, buf.line_number)
                    return True
                else:
                    char = buf.value()
                    data = data + char

                buf.rewind()
        else:
            buf.seek(pos)

        return False

    def __try_tokenize_whitespace(self, buf):
        ret = False
        while not buf.eof() and buf.value() == ' ':
            ret = True
            buf.rewind()

        return ret

    def __tokenize(self, buf):
        while not buf.eof():
            ret = (
                self.__try_tokenize_comment(buf) or
                self.__try_tokenize_slash_newline(buf) or
                self.__try_tokenize_simple_chars(buf) or
                self.__try_tokenize_quoted_literal(buf) or
                self.__try_tokenize_variable_or_literal(buf) or
                self.__try_tokenize_whitespace(buf) or
                self.__try_tokenize_multiline_literal(buf)
            )

            if not ret:
                Ui.parse_error(msg="unexpected character: " + str(buf.value()))

            if buf.eof():
                break

class SourceTree:
    def __init__(self):
        self.files = self.__find_pake_files()

    def __find_pake_files(self, path = os.getcwd()):
        ret = []
        for (dirpath, dirnames, filenames) in os.walk(path):
            for f in filenames:
                if not dirpath.startswith(FsUtils.BUILD_ROOT):
                    filename = dirpath + "/" + f
                    (base, ext) = os.path.splitext(filename)
                    if ext == ".pake":
                        ret.append(filename)
        return ret


class SourceTreeParser:
    def __init__(self, source_tree, variable_deposit, configuration_deposit, target_deposit):
        self.variable_deposit = variable_deposit
        self.configuration_deposit = configuration_deposit
        self.target_deposit = target_deposit
        self.modules = []

        for filename in source_tree.files:
            module = Module(
                self.variable_deposit,
                self.configuration_deposit,
                self.target_deposit,
                filename)

            self.modules.append(module)

        configuration = self.configuration_deposit.get_selected_configuration()
        self.variable_deposit.export_special_variables(configuration)


def main():
    parser = argparse.ArgumentParser(description='Painless buildsystem.')
    parser.add_argument('target', metavar='target', nargs="*", help='targets to be built')
    parser.add_argument('-a', '--all',  action="store_true", help='build all targets')
    parser.add_argument('-c', action='store', dest='configuration', default="__default", nargs="?", help='configuration to be used')
    args = parser.parse_args()
    Ui.debug(str(args))

    source_tree = SourceTree()
    variable_deposit = VariableDeposit()
    configuration_deposit = ConfigurationDeposit(args.configuration)
    target_deposit = TargetDeposit(variable_deposit, configuration_deposit, source_tree)
    parser = SourceTreeParser(source_tree, variable_deposit, configuration_deposit, target_deposit)

    Ui.bigstep("configuration", str(configuration_deposit.get_selected_configuration()))

    if len(args.target) > 0:
        for target in args.target:
            target_deposit.build(target)
    elif args.all:
        target_deposit.build_all()
    else:
        Ui.info(Ui.BOLD + "targets found in this source tree:" + Ui.RESET)
        Ui.info(str(target_deposit))

if __name__ == '__main__':
    main()

