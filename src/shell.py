import subprocess

import ui

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

