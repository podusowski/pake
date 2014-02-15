#!/usr/bin/env python

import os
import sys
import tempfile
import stat
import subprocess
import argparse
import marshal
import shutil
import threading

# local
import fsutils
import ui
import parsing
import compiler

"""
    utilities
"""

def execute(command, capture_output = False):
    out = ''
    try:
        if capture_output:
            out = subprocess.check_output(command, shell=True)
        else:
            subprocess.check_call(command, shell=True)
    except subprocess.CalledProcessError:
        raise Exception("command did not finish successfully: " + command)
        #ui.fatal("command did not finish successfully: " + command)

    ui.debug("command completed: " + command)
    return out

"""
    targets
"""
class CommonTargetParameters:
    def __init__(self, jobs, variable_deposit, root_path, module_name, name):
        assert isinstance(variable_deposit, VariableDeposit)
        assert isinstance(module_name, str)
        assert isinstance(name, str)

        self.jobs = jobs
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

        execute("mkdir -p " + fsutils.build_dir(configuration.name))

        ui.debug("building " + name + " with configuration " + str(configuration))
        ui.push()

        if name in self.built_targets:
            ui.debug(name + " already build, skipping")
            return
        else:
            self.built_targets.append(name)

        if not name in self.targets:
            ui.fatal("target " + name + " not found")

        target = self.targets[name]

        if not target.is_visible(configuration):
            ui.fatal("target " + name + " is not visible in " + str(configuration))

        evalueated_depends_on = self.variable_deposit.eval(
            target.common_parameters.module_name,
            target.common_parameters.depends_on)

        for dependency in evalueated_depends_on:
            ui.debug(name + " depends on " + dependency)
            self.build(dependency)

        toolchain = compiler.CxxToolchain(
            configuration,
            self.variable_deposit,
            target.common_parameters.name,
            self.source_tree)

        target.before()
        target.build(toolchain)
        target.after()
        target.copy_resources(toolchain)

        ui.pop()

    def build_all(self):
        ui.bigstep("building all targets", " ".join(self.targets))

        configuration = self.configuration_deposit.get_selected_configuration()

        for name in self.targets:
            target = self.targets[name]
            if target.is_visible(configuration):
                self.build(name)
            else:
                ui.bigstep("skip", name)

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
            ui.step("copy", resource)
            execute("rsync --update -r '" + resource + "' '" + toolchain.build_dir() + "/'")

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
            ui.debug("checking prerequisites (" + str(evaluated_prerequisites) + ") for making " + str(evaluated_artefacts))
            for artefact in evaluated_artefacts:
                ui.debug("  " + artefact)
                if fsutils.is_any_newer_than(evaluated_prerequisites, artefact):
                    ui.debug("going on because " + str(artefact) + " needs to be rebuilt")
                    should_run = True
                    break

        if should_run:
            self.common_parameters.variable_deposit.pollute_environment(self.common_parameters.module_name)

            evaluated_cmds = self.eval(cmds)

            for cmd in evaluated_cmds:
                ui.debug("running " + str(cmd))
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
        ui.debug("phony build")

class CompileableTarget(Target):
    def __init__(self, common_parameters, cxx_parameters):
        Target.__init__(self, common_parameters)

        self.common_parameters = common_parameters
        self.cxx_parameters = cxx_parameters
        self.error = False
        self.lock = threading.Lock()

    def __build_object(self, limit, toolchain, name, object_file, source, include_dirs, compiler_flags):
        limit.acquire()

        if self.error:
            limit.release()
            return

        try:
            toolchain.build_object(
                name,
                object_file,
                source,
                include_dirs,
                compiler_flags
            )
        except Exception as e:
            self.lock.acquire()
            ui.debug("catched " + str(e))
            self.error = True
            self.lock.release()
            limit.release()

        limit.release()

    def build_objects(self, toolchain):
        object_files = []
        evaluated_sources = self.eval(self.cxx_parameters.sources)
        evaluated_include_dirs = self.eval(self.cxx_parameters.include_dirs)
        evaluated_compiler_flags = self.eval(self.cxx_parameters.compiler_flags)

        ui.debug("building objects from " + str(evaluated_sources))
        ui.push()

        threads = []
        limit_semaphore = threading.Semaphore(self.common_parameters.jobs)

        for source in evaluated_sources:
            object_file = toolchain.object_filename(self.common_parameters.name, source)
            object_files.append(object_file)

            thread = threading.Thread(
                target=self.__build_object,
                args=(
                    limit_semaphore,
                    toolchain,
                    self.common_parameters.name,
                    object_file,
                    source,
                    evaluated_include_dirs,
                    evaluated_compiler_flags
                )
            )

            threads.append(thread)
            thread.daemon = True
            thread.start()

        done = False
        while not done:
            done = True
            for thread in threads:
                if thread.isAlive():
                    done = False
                    thread.join(0.1)

        if self.error:
            ui.fatal("cannot build " + self.common_parameters.name)

        ui.pop()

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

        if fsutils.is_any_newer_than(object_files, artefact):
            toolchain.link_static_library(artefact, object_files)
        else:
            ui.bigstep("up to date", artefact)

        os.chdir(root_dir)

"""
    parser
"""

class VariableDeposit:
    def __init__(self):
        self.modules = {}

    def export_special_variables(self, configuration):
        ui.debug("exporting special variables")
        ui.push()

        self.add_empty("__configuration", "$__null")
        self.add("__configuration", "$__name", parsing.Token.make_literal(configuration.name))
        for (value, name) in configuration.export:
            self.add("__configuration", name.content, value)

        for module in self.modules:
            self.add(module, "$__build", parsing.Token(parsing.Token.LITERAL, fsutils.build_dir(configuration.name)))

        ui.pop()

    def pollute_environment(self, current_module):
        ui.debug("polluting environment")
        ui.push()
        for module in self.modules:
            for (name, variable) in self.modules[module].iteritems():
                evaluated = self.eval(module, variable)
                env_name = module + "_" + name[1:]
                os.environ[env_name] = " ".join(evaluated)
                ui.debug("  " + env_name + ": " + str(evaluated))
                if module == current_module:
                    env_short_name = name[1:]
                    os.environ[env_short_name] = " ".join(evaluated)
                    ui.debug("  " + env_short_name + ": " + str(evaluated))
        ui.pop()

    def eval(self, current_module, l):
        ui.debug("evaluating " + str(l) + " in context of module " + current_module)
        ui.push()

        ret = []
        for token in l:
            if token.is_a(parsing.Token.LITERAL):
                content = self.__eval_literal(current_module, token.content)
                ui.debug("  " + token.content + " = " + content)
                ret.append(content)
            elif token.is_a(parsing.Token.VARIABLE):
                parts = token.content.split(".")

                ui.debug("dereferencing " + str(parts))

                module = ''
                name = ''
                if len(parts) == 1:
                    module = current_module
                    name = parts[0]
                elif len(parts) == 2:
                    module = parts[0][1:] # lose the $
                    name = "$" + parts[1]

                if not module in self.modules:
                    ui.parse_error(msg="no such module: " + module)

                # TODO: make some comment about __configuration variables
                if not name in self.modules[module]:
                    ui.fatal("dereferenced " + name + " but it doesn't exists in module " + module)

                for value in self.modules[module][name]:
                    if value.is_a(parsing.Token.VARIABLE):
                        re = self.eval(module, [value])
                        for v in re: ret.append(v)
                    else:
                        content = self.__eval_literal(module, value.content)
                        ret.append(content)
                        ui.debug("    = " + str(content))
            else:
                ui.parse_error(token)

        ui.debug(" = " + str(ret))
        ui.pop()
        return ret

    def __eval_literal(self, current_module, s):
        ui.debug("evaluating literal: " + s)
        ui.push()
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
                    ui.parse_error(msg="expecting { after $")
            elif state == STATE_READING_NAME:
                if c == "}":
                    ui.debug("variable: " + variable_name)
                    evaluated_variable = self.eval(current_module, [parsing.Token(parsing.Token.VARIABLE, variable_name)])
                    ret += " ".join(evaluated_variable)
                    variable_name = '$'
                    state = STATE_READING
                else:
                    variable_name += c
            elif state == STATE_READING_NAME:
                variable_name = variable_name + c

        ui.pop()
        return ret

    def add_empty(self, module_name, name):
        ui.debug("adding empty variable in module " + module_name + " called " + name)

        if not module_name in self.modules:
            self.modules[module_name] = {}

        self.modules[module_name][name] = []


    def add(self, module_name, name, value):
        ui.debug("adding variable in module " + module_name + " called " + name + " with value of " + str(value))

        if not module_name in self.modules:
            self.modules[module_name] = {}

        self.modules[module_name][name] = [value]

    def append(self, module_name, name, value):
        ui.debug("appending variable in module " + module_name + " called " + name + " with value of " + str(value))

        if not module_name in self.modules:
            self.modules[module_name] = {}

        if not name in self.modules[module_name]:
            self.modules[module_name][name] = []

        self.modules[module_name][name].append(value)
        ui.debug("  new value: " + str(self.modules[module_name][name]))

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
        configuration = compiler.Configuration()
        self.add_configuration(configuration)

class Module:
    def __init__(self, jobs, variable_deposit, configuration_deposit, target_deposit, filename):
        assert isinstance(variable_deposit, VariableDeposit)
        assert isinstance(filename, str)

        ui.debug("parsing " + filename)
        ui.push()

        self.jobs = jobs
        self.variable_deposit = variable_deposit
        self.configuration_deposit = configuration_deposit
        self.target_deposit = target_deposit
        self.filename = filename
        self.name = self.__get_module_name(filename)
        self.lines = []
        self.targets = []
        self.base_dir = os.path.dirname(filename)

        tokenizer = parsing.Tokenizer(filename)
        self.tokens = tokenizer.tokens

        self.__parse()

        self.variable_deposit.add(
            self.name,
            "$__path",
            parsing.Token.make_literal(os.path.dirname(self.filename)))

        self.variable_deposit.add_empty(
            self.name,
            "$__null")

        ui.pop()

    def __get_module_name(self, filename):
        base = os.path.basename(filename)
        (root, ext) = os.path.splitext(base)
        return root

    def __add_target(self, target):
        ui.debug("adding target: " + str(target))
        self.targets.append(target)
        self.target_deposit.add_target(target)

    def __parse_set_or_append(self, it, append):
        token = it.next()
        if token.is_a(parsing.Token.VARIABLE):
            variable_name = token.content
        else:
            ui.parse_error(token)

        second_add = False
        while True:
            token = it.next()
            if token.is_a(parsing.Token.LITERAL) or token.is_a(parsing.Token.VARIABLE):
                if append or second_add:
                    self.variable_deposit.append(self.name, variable_name, token)
                else:
                    self.variable_deposit.add(self.name, variable_name, token)
                    second_add = True

            elif token.is_a(parsing.Token.NEWLINE):
                break
            else:
                ui.parse_error(token)

    # (something1 something2)
    def __parse_list(self, it):
        ret = []
        token = it.next()
        if token.is_a(parsing.Token.OPEN_PARENTHESIS):

            while True:
                token = it.next()
                if token.is_a(parsing.Token.LITERAL):
                    ret.append(token)
                elif token.is_a(parsing.Token.VARIABLE):
                    ret.append(token)
                elif token.is_a(parsing.Token.CLOSE_PARENTHESIS):
                    break
                else:
                    ui.parse_error(token)
        else:
            ui.parse_error(token)

        return ret

    # ($var1:$var2 something4:$var1)
    def __parse_colon_list(self, it):
        ret = []
        token = it.next()
        if token.is_a(parsing.Token.OPEN_PARENTHESIS):

            while True:
                token = it.next()

                first = None
                second = None

                if token.is_a(parsing.Token.LITERAL) or token.is_a(parsing.Token.VARIABLE):
                    first = token
                    token = it.next()
                    if token.is_a(parsing.Token.COLON):
                        token = it.next()
                        if token.is_a(parsing.Token.VARIABLE):
                            second = token
                            ret.append((first, second))
                        else:
                            ui.parse_error(token, msg="expected variable")
                    else:
                        ui.parse_error(token, msg="expected colon")
                elif token.is_a(parsing.Token.CLOSE_PARENTHESIS):
                    break
                else:
                    ui.parse_error(token)
        else:
            ui.parse_error(token)

        ui.debug("colon list: " + str(ret))
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
            self.jobs,
            self.variable_deposit,
            os.path.dirname(self.filename),
            self.name,
            target_name)

        cxx_parameters = CxxParameters()

        while True:
            token = it.next()
            if token.is_a(parsing.Token.LITERAL):
                if self.__try_parse_target_common_parameters(common_parameters, token, it): pass
                elif self.__try_parse_cxx_parameters(cxx_parameters, token, it): pass
                elif token.content == "link_with": link_with = self.__parse_list(it)
                elif token.content == "library_dirs": library_dirs = self.__parse_list(it)
                else: ui.parse_error(token)
            elif token.is_a(parsing.Token.NEWLINE):
                break
            else:
                ui.parse_error(token)

        target = Application(common_parameters, cxx_parameters, link_with, library_dirs)
        self.__add_target(target)

    def __parse_static_library(self, target_name, it):
        common_parameters = CommonTargetParameters(
            self.jobs,
            self.variable_deposit,
            os.path.dirname(self.filename),
            self.name,
            target_name)

        cxx_parameters = CxxParameters()

        while True:
            token = it.next()
            if token.is_a(parsing.Token.LITERAL):
                if self.__try_parse_target_common_parameters(common_parameters, token, it): pass
                elif self.__try_parse_cxx_parameters(cxx_parameters, token, it): pass
                else: ui.parse_error(token)
            elif token.is_a(parsing.Token.NEWLINE):
                break
            else:
                ui.parse_error(token)

        target = StaticLibrary(common_parameters, cxx_parameters)
        self.__add_target(target)

    def __parse_phony(self, target_name, it):
        common_parameters = CommonTargetParameters(
            self.jobs,
            self.variable_deposit,
            os.path.dirname(self.filename),
            self.name,
            target_name)

        cxx_parameters = CxxParameters()

        while True:
            token = it.next()
            if token.is_a(parsing.Token.LITERAL):
                if self.__try_parse_target_common_parameters(common_parameters, token, it): pass
                elif token.content == "artefacts": common_parameters.artefacts = self.__parse_list(it)
                elif token.content == "prerequisites": common_parameters.prerequisites = self.__parse_list(it)
                else: ui.parse_error(token)

            elif token.is_a(parsing.Token.NEWLINE):
                break
            else:
                ui.parse_error(token)

        target = Phony(common_parameters)
        self.__add_target(target)

    def __parse_target(self, it):
        token = it.next()
        if token.is_a(parsing.Token.LITERAL):
            target_type = token.content

            token = it.next()
            if token.is_a(parsing.Token.LITERAL):
                target_name = token.content
            else:
                ui.parse_error(token)
        else:
            ui.parse_error(token)

        if target_type == "application":       self.__parse_application_target(target_name, it)
        elif target_type == "static_library":  self.__parse_static_library(target_name, it)
        elif target_type == "phony":           self.__parse_phony(target_name, it)
        else: ui.parse_error(token, msg="unknown target type: " + target_type)

    def __parse_configuration(self, it):
        configuration = compiler.Configuration()

        # name
        token = it.next()
        if token.is_a(parsing.Token.LITERAL):
            configuration.name = token.content
        else:
            ui.parse_error(token)

        while True:
            token = it.next()
            if token.is_a(parsing.Token.LITERAL):
                if token.content == "compiler": configuration.compiler = self.__parse_list(it)
                elif token.content == "archiver": configuration.archiver = self.__parse_list(it)
                elif token.content == "application_suffix": configuration.application_suffix = self.__parse_list(it)
                elif token.content == "compiler_flags": configuration.compiler_flags = self.__parse_list(it)
                elif token.content == "linker_flags": configuration.linker_flags = self.__parse_list(it)
                elif token.content == "export": configuration.export = self.__parse_colon_list(it)
                else: ui.parse_error(token)

            elif token.is_a(parsing.Token.NEWLINE):
                break
            else:
                ui.parse_error(token)

        ui.debug("configuration parsed:" + str(configuration))
        self.configuration_deposit.add_configuration(configuration)

    def __parse_directive(self, it):
        while True:
            token = it.next()

            if token.is_a(parsing.Token.LITERAL):
                if token.content == "set" or token.content == "append": self.__parse_set_or_append(it, token.content == "append")
                elif token.content == "target":                    self.__parse_target(it)
                elif token.content == "configuration":             self.__parse_configuration(it)
                else: ui.parse_error(token, msg="expected directive")

            elif token.is_a(parsing.Token.NEWLINE):
                continue
            else:
                return False

    def __parse(self):
        it = iter(self.tokens)

        try:
            if not self.__parse_directive(it):
                ui.parse_error(msg="unknown :(")
        except StopIteration:
            ui.debug("eof")

class SourceTree:
    def __init__(self):
        self.files = self.__find_pake_files()

    def __find_pake_files(self, path = os.getcwd()):
        ret = []
        for (dirpath, dirnames, filenames) in os.walk(path):
            for f in filenames:
                if not dirpath.startswith(fsutils.BUILD_ROOT):
                    filename = dirpath + "/" + f
                    (base, ext) = os.path.splitext(filename)
                    if ext == ".pake":
                        ret.append(filename)
        return ret


class SourceTreeParser:
    def __init__(self, jobs, source_tree, variable_deposit, configuration_deposit, target_deposit):
        self.jobs = jobs
        self.variable_deposit = variable_deposit
        self.configuration_deposit = configuration_deposit
        self.target_deposit = target_deposit
        self.modules = []

        for filename in source_tree.files:
            module = Module(
                self.jobs,
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
    parser.add_argument('-j', action='store', dest='jobs', default="1", nargs="?", help='parallel jobs to be used')
    args = parser.parse_args()
    ui.debug(str(args))

    source_tree = SourceTree()
    variable_deposit = VariableDeposit()
    configuration_deposit = ConfigurationDeposit(args.configuration)
    target_deposit = TargetDeposit(variable_deposit, configuration_deposit, source_tree)
    parser = SourceTreeParser(int(args.jobs), source_tree, variable_deposit, configuration_deposit, target_deposit)

    ui.bigstep("configuration", str(configuration_deposit.get_selected_configuration()))

    if len(args.target) > 0:
        for target in args.target:
            target_deposit.build(target)
    elif args.all:
        target_deposit.build_all()
    else:
        ui.info(ui.BOLD + "targets found in this source tree:" + ui.RESET)
        ui.info(str(target_deposit))

if __name__ == '__main__':
    main()

