import os
import sys
import threading

RESET = '\033[0m'
BOLD = '\033[1m'
GRAY = '\033[90m'
RED = '\033[31m'
BOLD_RED = '\033[1;31m'
BOLD_BLUE = "\033[34;1m"

_log_depth = 0
_lock = threading.Lock()

class Ident:
    def __enter__(self):
        global _log_depth
        with _lock:
            _log_depth += 1

    def __exit__(self, *args):
        global _log_depth
        with _lock:
            _log_depth -= 1

ident = Ident()

def push():
    global _log_depth

    with _lock:
        _log_depth += 1

def pop():
    global _log_depth

    with _lock:
        _log_depth -= 1

def print_depth_prefix():
    global _log_depth

    for i in range(_log_depth):
        sys.stdout.write("    ")

def info(message):
    with _lock:
        print(message)
        sys.stdout.flush()

def step(tool, parameter):
    with _lock:
        if sys.stdout.isatty():
            print(BOLD + tool + RESET + " " + parameter)
        else:
            print(tool + " " + parameter)
        sys.stdout.flush()

def bigstep(tool, parameter):
    with _lock:
        if sys.stdout.isatty():
            print(BOLD_BLUE + tool + RESET + " " + parameter)
        else:
            print(tool + " " + parameter)
        sys.stdout.flush()

def fatal(message):
    with _lock:
        if sys.stdout.isatty():
            print(BOLD_RED + "fatal: " + RESET + message)
        else:
            print("fatal: " + message)
        sys.stdout.flush()
        sys.exit(1)

def parse_error(token = None, msg = None):
    if token != None:
        s = token.location_str()
        if msg != None:
            s += ": " + msg
        else:
            s += ": unexpected " + str(token)
        fatal(s)
    else:
        fatal(msg)

def debug(s, env = None):
    if "DEBUG" in os.environ:
        with _lock:
            if env == None or env in os.environ:
                print_depth_prefix()
                print(GRAY + s + RESET)


