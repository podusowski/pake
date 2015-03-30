#!/usr/bin/env python

import fsutils
import ui
import targets
import variables
import configurations
import parser
import command_line

def parse_source_tree():
    for filename in fsutils.pake_files:
        parser.parse(filename)

    configuration = configurations.get_selected_configuration()
    variables.export_special_variables(configuration)


def _build_some_targets_if_requested():
    if command_line.args.target:
        for target in command_line.args.target:
            targets.build(target)
        return True
    elif command_line.args.all:
        targets.build_all()
        return True


def main():
    parse_source_tree()

    configuration = configurations.get_selected_configuration()
    if configuration.name != "__default":
        ui.bigstep("configuration", str(configurations.get_selected_configuration()))

    if not _build_some_targets_if_requested():
        ui.info("no target selected\n")

        ui.info(ui.BOLD + "targets:" + ui.RESET)
        for target in targets.targets.values():
            ui.info("  " + str(target))

        ui.info(ui.BOLD + "\nconfigurations:" + ui.RESET)
        for configuration in configurations.configurations:
            ui.info("  " + str(configuration))

        ui.info("\nsee --help for more\n")

if __name__ == '__main__':
    main()

