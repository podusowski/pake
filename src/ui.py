import os
import sys
import threading

RESET = '\033[0m'
BOLD = '\033[1m'
GRAY = '\033[90m'
RED = '\033[31m'
BOLD_YELLOW = '\033[1;33m'
BOLD_RED = '\033[1;31m'
BOLD_BLUE = "\033[34;1m"

_log_depth = 0
_lock = threading.Lock()


class _Ident:
    def __enter__(self):
        global _log_depth
        with _lock:
            _log_depth += 1

    def __exit__(self, *args):
        global _log_depth
        with _lock:
            _log_depth -= 1


ident = _Ident()


def _fancy_print(base_text, color="", additional_text=""):
    with _lock:
        if sys.stdout.isatty():
            print("{}{}{} {}".format(color, base_text, RESET, additional_text))
        else:
            print("{} {}".format(base_text, additional_text))
        sys.stdout.flush()


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
    _fancy_print(tool, BOLD, parameter)


def bigstep(tool, parameter):
    _fancy_print(tool, BOLD_BLUE, parameter)


def warning(message):
    _fancy_print("warning:", BOLD_YELLOW, message)


def fatal(message):
    _fancy_print("fatal:", BOLD_RED, message)
    sys.exit(1)


def parse_error(token=None, msg=None):
    if token is not None:
        s = str(token.location)
        if msg is not None:
            s += ": " + msg
        else:
            s += ": unexpected " + str(token)
        fatal(s)
    else:
        fatal(msg)


def debug(s):
    if "DEBUG" in os.environ:
        with _lock:
            print_depth_prefix()
            print(GRAY + s + RESET)
