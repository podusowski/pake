import os
import threading
import subprocess

import ui
import fsutils
import compiler
import shell
import variable_deposit

class TargetDeposit:
    def __init__(self, configuration_deposit):
        self.configuration_deposit = configuration_deposit
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

        fsutils.make_build_dir(configuration.name)

        ui.debug("building " + name + " with configuration " + str(configuration))

        with ui.ident:
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

            evalueated_depends_on = variable_deposit.eval(
                target.common_parameters.module_name,
                target.common_parameters.depends_on)

            for dependency in evalueated_depends_on:
                ui.debug(name + " depends on " + dependency)
                self.build(dependency)

            toolchain = compiler.CxxToolchain(
                configuration,
                None,
                target.common_parameters.name,
                None)

            target.before()
            target.build(toolchain)
            target.after()
            target.copy_resources(toolchain)

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
            shell.execute("rsync --update -r '" + resource + "' '" + toolchain.build_dir() + "/'")

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
            variable_deposit.pollute_environment(self.common_parameters.module_name)

            evaluated_cmds = self.eval(cmds)

            for cmd in evaluated_cmds:
                ui.debug("running " + str(cmd))
                shell.execute(cmd)

        os.chdir(root_dir)

    def eval(self, variable):
        return variable_deposit.eval(
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

    def __build_object(self, jobs_semaphore, toolchain, name, object_file, source, include_dirs, compiler_flags):
        with jobs_semaphore:
            if self.error:
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
                ui.debug("catched during compilation " + str(e))
                self.error = True

    def build_objects(self, toolchain):
        object_files = []
        evaluated_sources = self.eval(self.cxx_parameters.sources)
        evaluated_include_dirs = self.eval(self.cxx_parameters.include_dirs)
        evaluated_compiler_flags = self.eval(self.cxx_parameters.compiler_flags)

        ui.debug("building objects from " + str(evaluated_sources))
        ui.push()

        threads = []

        import command_line
        limit_semaphore = threading.Semaphore(int(command_line.args.jobs))

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


