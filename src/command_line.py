import argparse

import ui

def _parse_command_line():
    parser = argparse.ArgumentParser(description='Painless buildsystem.')
    parser.add_argument('target', metavar='target', nargs="*", help='targets to be built')
    parser.add_argument('-a', '--all',  action="store_true", help='build all targets')
    parser.add_argument('-c', action='store', dest='configuration', default="__default", nargs="?", help='configuration to be used')
    parser.add_argument('-j', action='store', dest='jobs', default="1", nargs="?", help='parallel jobs to be used')
    args = parser.parse_args()
    ui.debug(str(args))
    return args

args = _parse_command_line()

