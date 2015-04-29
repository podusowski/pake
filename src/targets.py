import os
import threading

import ui
import fsutils
import compiler
import shell
import variables
import configurations
import command_line

targets = {}
_built_targets = []


def add_target(target):
    ui.debug("adding target: {!s}".format(target))

    targets[target.common_parameters.name] = target

def _build_and_track_single_target(name):
    """ tracking means putting it to special
        container, when this function is called
        with the same target, it will be skipped """
    configuration = configurations.get_selected_configuration()

    fsutils.make_build_dir(configuration.name)

    ui.debug("building {} with configuration {!s}".format(name, configuration))

    with ui.ident:
        if name in _built_targets:
            ui.debug("{} already build, skipping".format(name))
            return
        else:
            _built_targets.append(name)

        if name not in targets:
            ui.fatal("target {} not found".format(name))

        target = targets[name]

        if not target.is_visible(configuration):
            ui.fatal("target {} is not visible in {!s}"
                     .format(name, configuration))

        for dependency in target.common_parameters.depends_on.eval():
            ui.debug("{} depends on {}".format(name, dependency))
            build(dependency)

        toolchain = compiler.Gnu()

        target.before()
        target.build(toolchain)
        target.after()
        target.copy_resources(toolchain)


def _clear_tracked_targets():
    _built_targets = []


def build(name):
    _build_and_track_single_target(name)
    _clear_tracked_targets()


def build_all():
    ui.bigstep("building all targets", " ".join(targets))

    configuration = configurations.get_selected_configuration()

    for name, target in targets.items():
        if target.is_visible(configuration):
            _build_and_track_single_target(name)
        else:
            ui.bigstep("skip", name)

    _clear_tracked_targets()


class Target:
    def __init__(self, common_parameters):
        self.common_parameters = common_parameters

    def __str__(self):

        def decorate_not_empty(phrase, prefix):
            return [str(prefix) + str(phrase)] if phrase else []

        ra = decorate_not_empty(self.common_parameters.run_after, "run after: ")
        rb = decorate_not_empty(self.common_parameters.run_before, "run before: ")

        return '{: <24} {: <24} {}'.format(ui.BOLD + self.type_string() + ui.RESET,
                                        self.common_parameters.name,
                                        ', '.join([] + ra + rb))

    def before(self):
        self.__try_run(self.common_parameters.run_before)

    def after(self):
        self.__try_run(self.common_parameters.run_after)

    def copy_resources(self, toolchain):
        root_dir = os.getcwd()
        os.chdir(self.common_parameters.root_path)

        for resource in self.common_parameters.resources.eval():
            ui.step("copy", resource)
            shell.execute("rsync --update -r '{resource}' '{build_dir}/'"
                          .format(resource=resource,
                                  build_dir=toolchain.build_dir()))

        os.chdir(root_dir)

    def is_visible(self, configuration):
        evaluated_visible_in = self.common_parameters.visible_in.eval()

        if evaluated_visible_in:
            return configuration.name in evaluated_visible_in

        return True

    def __are_explicit_prerequisities_newer(self, artefacts, prerequisites):
        ui.debug("checking prerequisites ({!s}) for making {!s}"
                 .format(prerequisites, artefacts))

        if prerequisites and artefacts:
            for artefact in artefacts:
                ui.debug("  " + artefact)
                if fsutils.is_any_newer_than(prerequisites, artefact):
                    ui.debug(("going on because {!s}"
                              "needs to be rebuilt").format(artefact))
                    return True
            return False
        else:
            return True

    def __try_run(self, cmds):
        evaluated_cmds = cmds.eval()

        if evaluated_cmds:
            root_dir = os.getcwd()
            os.chdir(self.common_parameters.root_path)

            evaluated_artefacts = self.common_parameters.artefacts.eval()
            evaluated_prerequisites = self.common_parameters.prerequisites.eval()

            should_run = self.__are_explicit_prerequisities_newer(evaluated_artefacts,
                                                                  evaluated_prerequisites)

            if should_run:
                variables.pollute_environment(self.common_parameters.module_name)

                for cmd in evaluated_cmds:
                    ui.debug("running {!s}".format(cmd))
                    shell.execute(cmd)

            os.chdir(root_dir)


class Phony(Target):
    def __init__(self, common_parameters):
        Target.__init__(self, common_parameters)

    def type_string(self):
        return "phony"

    def build(self, configuration):
        evaluated_artefacts = self.common_parameters.artefacts.eval()
        evaluated_prerequisites = self.common_parameters.prerequisites.eval()

        if not evaluated_artefacts or not evaluated_prerequisites:
            ui.warning(("target {} has no artifacts or prerequisites defined, "
                        "this means, whatever is defined in run_before or run_after "
                        "will be always executed")
                       .format(self.common_parameters.name))

        ui.debug("phony build")


class CompileableTarget(Target):
    def __init__(self, common_parameters, cxx_parameters):
        Target.__init__(self, common_parameters)

        self.common_parameters = common_parameters
        self.cxx_parameters = cxx_parameters
        self.error = False

    def _build_object(self, sem, toolchain, name, object_file,
                       source, include_dirs, compiler_flags):
        try:
            if self.error:
                return

            with sem:
                toolchain.build_object(name, object_file, source, include_dirs, compiler_flags)
        except Exception as e:
            ui.debug("catched during compilation {!s}".format(e))
            self.error_reason = str(e)
            self.error = True

    def build_objects(self, toolchain):
        object_files = []
        evaluated_sources = self.cxx_parameters.sources.eval()
        evaluated_include_dirs = self.cxx_parameters.include_dirs.eval()
        evaluated_compiler_flags = self.cxx_parameters.compiler_flags.eval()

        ui.debug("building objects from {!s}".format(evaluated_sources))
        ui.push()

        threads = []

        jobs = command_line.args.jobs
        limit_semaphore = threading.Semaphore(int(jobs))
        ui.debug("limiting jobs to {!s}".format(jobs))

        for source in evaluated_sources:
            object_file = toolchain.object_filename(self.common_parameters.name,
                                                        source)
            object_files.append(object_file)

            thread = threading.Thread(target=self._build_object,
                                      args=(limit_semaphore, toolchain, self.common_parameters.name, object_file,
                                            source, evaluated_include_dirs, evaluated_compiler_flags))

            threads.append(thread)
            thread.daemon = True
            thread.start()

        assert len(threads) <= jobs

        for t in threads:
            t.join()

        if self.error:
            ui.fatal("failed building {!s}: {!s}"
                     .format(self.common_parameters.name, self.error_reason))

        ui.pop()

        return object_files


class Application(CompileableTarget):
    def __init__(self, common_parameters, cxx_parameters, link_with, library_dirs):
        CompileableTarget.__init__(self, common_parameters, cxx_parameters)

        self.link_with = link_with
        self.library_dirs = library_dirs

    def type_string(self):
        return "application"

    def build(self, toolchain):
        root_dir = os.getcwd()
        os.chdir(self.common_parameters.root_path)

        object_files = self.build_objects(toolchain)

        toolchain.link_application(toolchain.application_filename(self.common_parameters.name),
                                   object_files, self.link_with.eval(), self.library_dirs.eval())

        os.chdir(root_dir)


class StaticLibrary(CompileableTarget):
    def __init__(self, common_parameters, cxx_parameters):
        CompileableTarget.__init__(self, common_parameters, cxx_parameters)

    def type_string(self):
        return "static_library"

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
