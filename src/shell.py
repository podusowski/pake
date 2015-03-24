import subprocess

import ui

_counter = 0

def execute(command, capture_output = False):
    global _counter

    _counter += 1

    ui.debug("running {!s}: {!s}".format(_counter, command))

    out = ''
    try:
        if capture_output:
            out = subprocess.check_output(command, shell=True)
        else:
            subprocess.check_call(command, shell=True)
    except subprocess.CalledProcessError as e:
        raise Exception("command exited with error({}): {}".format(str(e.returncode), command))

    return out

