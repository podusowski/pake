import os
import sys
import threading

RESET = '\033[0m'
BOLD = '\033[1m'
GRAY = '\033[90m'
RED = '\033[31m'
BOLD_RED = '\033[1;31m'
BOLD_BLUE = "\033[34;1m"

log_depth = 0
lock = threading.Lock()

def push():
    global log_depth

    lock.acquire()
    log_depth += 1
    lock.release()

def pop():
    global log_depth

    lock.acquire()
    log_depth -= 1
    lock.release()

def print_depth_prefix():
    global log_depth

    for i in range(log_depth):
        sys.stdout.write("    ")

def info(message):
    lock.acquire()
    print(message)
    sys.stdout.flush()
    lock.release()

def step(tool, parameter):
    lock.acquire()
    if sys.stdout.isatty():
        print(BOLD + tool + RESET + " " + parameter)
    else:
        print(tool + " " + parameter)
    sys.stdout.flush()
    lock.release()

def bigstep(tool, parameter):
    lock.acquire()
    if sys.stdout.isatty():
        print(BOLD_BLUE + tool + RESET + " " + parameter)
    else:
        print(tool + " " + parameter)
    sys.stdout.flush()
    lock.release()

def fatal(message):
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
    lock.acquire()
    if "DEBUG" in os.environ:
        if env == None or env in os.environ:
            print_depth_prefix()
            print(GRAY + s + RESET)
    lock.release()


