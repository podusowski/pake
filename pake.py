#!/usr/bin/env python

import os
import sys
import tempfile
import stat

RESET = '\033[0m'
BOLD = '\033[1m'
GRAY = '\033[90m'
RED = '\033[31m'
BOLD_RED = '\033[1;31m'
BUILD_DIR = "_build"

"""
    utilities
"""

def is_newer_than(prerequisite, target):
    if os.path.exists(target):
        return os.path.getmtime(prerequisite) > os.path.getmtime(target)
    else:
        return True

def is_any_newer_than(prerequisites, target):
    for prerequisite in prerequisites:
        if is_newer_than(prerequisite, target):
            return True
    return False

def execute(command):
    f = os.popen(command)
    out = f.read()
    ret = f.close()
    if ret != None:
        debug("error in command: " + command)
        raise Exception("error in command: " + command)

    debug("command completed: " + command)
    return out

"""
    C++ compiler support
"""

class CxxCompiler:
    def __init__(self):
        self.compiler_cmd = "c++"
        self.compiler_flags = "-I."

    def build(self, out_filename, in_filename):
        prerequisites = self.__scan_includes(in_filename)
        prerequisites.append(in_filename)

        if is_any_newer_than(prerequisites, out_filename):
            info(BOLD + "c++" + RESET + " " + in_filename)
            execute("mkdir -p " + os.path.dirname(out_filename))
            execute(self.compiler_cmd + " " + self.compiler_flags + " -c -o " + out_filename + " " + in_filename)

    def __scan_includes(self, in_filename):
        debug("scanning includes for " + in_filename)
        ret = []
        out = execute(self.compiler_cmd + " " + self.compiler_flags + " -M " + in_filename).split()
        for token in out[2:]:
            if token != "\\":
                ret.append(token)
        return ret

class CxxLinker:
    def build(self, out_filename, in_filenames, link_with):
        if is_any_newer_than(in_filenames, out_filename) or self.__are_libs_newer_than_target(link_with, out_filename):
            debug("link " + str(in_filenames) + ", with libs: " + str(link_with) + " -> " + out_filename)
            info(BOLD + "linking " + RESET + out_filename)
            execute("c++ -o " + out_filename + " " + " ".join(in_filenames) + " " + self.__libs_arguments(link_with))
        else:
            info(BOLD + out_filename + RESET + " is up to date")

    def __libs_arguments(self, link_with):
        ret = "-L " + BUILD_DIR + " "
        for lib in link_with:
            ret = ret + " -l" + lib
        return ret

    def __are_libs_newer_than_target(self, link_with, target):
        # just look at BUILD_DIR and check if lib exiss there
        for lib in link_with:
            # TODO: filenames!
            if is_newer_than(BUILD_DIR + "/lib" + lib + ".a", target):
                return True
        return False

class CxxArchiver:
    def build(self, out_filename, in_filenames):
        if is_any_newer_than(in_filenames, out_filename):
            info(BOLD + "archiving " + RESET + out_filename)
            execute("ar -rcs " + out_filename + " " + " ".join(in_filenames))
        else:
            info(BOLD + out_filename + RESET + " is up to date")

"""
    targets
"""

class Target:
    def __init__(self, name, depends_on, run_after):
        self.name = name
        self.depends_on = depends_on
        self.run_after = run_after
        debug("run_after: " + str(self.run_after))

    def __str__(self):
        return self.name

    def after(self):
        if self.run_after != None:
            debug("running " + str(self.run_after))
            execute(self.run_after)

            #filename = ""
            #try:
            #    (fd, filename) = tempfile.mkstemp()
            #    f = os.fdopen(fd, "w")
            #    f.write(self.run_after)
            #    f.close()

            #    st = os.stat(filename)
            #    os.chmod(filename, st.st_mode | stat.S_IEXEC)
            #    execute(filename)
            #finally:
            #    os.unlink(filename)

class Phony(Target):
    def __init__(self, name, depends_on, run_after):
        Target.__init__(self, name, depends_on, run_after)

    def build(self):
        debug("phony build")

class Application(Target):
    def __init__(self, name, depends_on, run_after, sources, link_with):
        Target.__init__(self, name, depends_on, run_after)

        self.sources = sources
        self.link_with = link_with
        self.compiler = CxxCompiler()
        self.linker = CxxLinker()

    def build(self):
        object_files = []
        debug("building application from " + str(self.sources))
        for source in self.sources:
            object_file = self.__object_filename(source)
            object_files.append(object_file)
            self.compiler.build(object_file, source)

        self.linker.build(self.__app_filename(self.name), object_files, self.link_with)

    def __object_filename(self, in_filename):
        out = BUILD_DIR + "/build." + self.name + "/" + in_filename + ".o"
        return out

    def __app_filename(self, target_name):
        return BUILD_DIR + "/" + self.name

class StaticLibrary(Target):
    def __init__(self, name, depends_on, run_after, sources):
        Target.__init__(self, name, depends_on, run_after)

        self.sources = sources
        self.compiler = CxxCompiler()
        self.linker = CxxArchiver()

    def build(self):
        object_files = []
        debug("building static_library from " + str(self.sources))
        for source in self.sources:
            object_file = self.__object_filename(source)
            self.compiler.build(object_file, source)
            object_files.append(object_file)

        self.linker.build(self.__lib_filename(), object_files)

    def __object_filename(self, in_filename):
        out = BUILD_DIR + "/build." + self.name + "/" + in_filename + ".o"
        return out

    def __lib_filename(self):
        return BUILD_DIR + "/lib" + self.name + ".a"

"""
    parser
"""

class ParsingError(Exception):
    def __init__(self, token, hint = None):
        self.token = token
        self.hint = hint

        import traceback, os.path
        self.traceback = traceback.extract_stack()

    def __str__(self):
        (t, c) = self.token
        msg = "parsing error, unexpected token: " + str(t) + "|" + str(c)
        if self.hint != None:
            msg = msg + ", hint: " + self.hint

        msg = msg + "\ntraceback:\n"
        for i in self.traceback:
            msg = msg + str(i) + "\n"
        return msg

class Variable:
    def __init__(token):
        self.token = token

    def value():
        return self.value

class VariableDeposit:
    def __init__(self):
        modules = {}

    def eval(self, current_module, variable_name):
        parts = variable_name.split(".")
        debug(str(len(parts)))

    def add(self, module_name, name, value):
        pass

    def append(self, module_name, name, value):
        pass

class PakeFile:
    def __init__(self, variable_deposit, filename):
        assert isinstance(variable_deposit, VariableDeposit)
        assert isinstance(filename, str)

        debug("parsing " + filename)

        self.variable_deposit = variable_deposit
        self.filename = filename
        self.name = filename # TODO: loose extension
        self.lines = []
        self.variables = {}
        self.targets = []
        self.base_dir = os.path.dirname(filename)

        tokenizer = Tokenizer(filename)
        self.tokens = tokenizer.tokens

        self.__parse()

        debug("variables: " + str(self.variables))

    def __add_target(self, target):
        debug("adding target: " + str(target) + ", depends_on: " + str(target.depends_on))
        self.targets.append(target)

    def __parse_set_or_append(self, it, append):
        token = it.next()
        if token[0] == Tokenizer.TOKEN_VARIABLE:
            variable_name = token[1]
        else:
            raise ParsingError(token)

        if not append:
            self.variables[variable_name] = []

        while True:
            token = it.next()
            if token[0] == Tokenizer.TOKEN_LITERAL:
                self.variables[variable_name].append(token[1])
                debug("new variable value: " + variable_name + ": " + str(self.variables[variable_name]))

                if append:
                    self.variable_deposit.append(self.name, variable_name, token[1])
                else:
                    self.variable_deposit.add(self.name, variable_name, token[1])

            elif token[0] == Tokenizer.TOKEN_NEWLINE:
                break
            else:
                raise ParsingError(token)

    def __parse_list(self, it):
        ret = []
        token = it.next()
        if token[0] == Tokenizer.TOKEN_OPEN_PARENTHESIS:

            while True:
                token = it.next()
                if token[0] == Tokenizer.TOKEN_LITERAL:
                    ret.append(token[1])
                elif token[0] == Tokenizer.TOKEN_VARIABLE:
                    for v in self.variables[token[1]]:
                        ret.append(v)
                elif token[0] == Tokenizer.TOKEN_CLOSE_PARENTHESIS:
                    break
                else:
                    raise ParsingError(token)
        else:
            raise ParsingError(token)

        return ret

    def __parse_literal(self, it):
        token = it.next()

        if token[0] in [Tokenizer.TOKEN_LITERAL, Tokenizer.TOKEN_MULTILINE_LITERAL]:
            return token[1]
        else:
            raise ParsingError(token)

    def __parse_run_after(self, it):
        while True:
            token = it.next()
            if token[0] == Tokenizer.TOKEN_OPEN_PARENTHESIS:
                run_after = self.__parse_literal(it)
                token = it.next()
                if token[0] == Tokenizer.TOKEN_CLOSE_PARENTHESIS: return run_after
                else: raise ParsingError(Token)
            else:
                raise ParsingError(Token)

    def __parse_application_target(self, target_name, it):
        link_with = []
        depends_on = []
        run_after = None

        while True:
            token = it.next()
            if token[0] == Tokenizer.TOKEN_LITERAL:
                if token[1] == "sources": sources = self.__parse_list(it)
                elif token[1] == "link_with": link_with = self.__parse_list(it)
                elif token[1] == "depends_on": depends_on = self.__parse_list(it)
                elif token[1] == "run_after": run_after = self.__parse_run_after(it)
                else: raise ParsingError(token)
            elif token[0] == Tokenizer.TOKEN_NEWLINE:
                break
            else:
                raise ParsingError(token)

        target = Application(target_name, depends_on, run_after, sources, link_with)
        self.__add_target(target)

    def __parse_static_library(self, target_name, it):
        depends_on = []
        run_after = None

        while True:
            token = it.next()
            if token[0] == Tokenizer.TOKEN_LITERAL:
                if token[1] == "sources": sources = self.__parse_list(it)
                elif token[1] == "depends_on": depends_on = self.__parse_list(it)
                elif token[1] == "run_after": run_after = self.__parse_run_after(it)
                else: raise ParsingError()
            elif token[0] == Tokenizer.TOKEN_NEWLINE:
                break
            else:
                raise ParsingError()

        target = StaticLibrary(target_name, depends_on, run_after, sources)
        self.__add_target(target)

    def __parse_phony(self, target_name, it):
        depends_on = []
        run_after = None

        while True:
            token = it.next()
            if token[0] == Tokenizer.TOKEN_LITERAL:
                if   token[1] == "depends_on": depends_on = self.__parse_list(it)
                elif token[1] == "run_after": run_after = self.__parse_run_after(it)
                else: raise ParsingError(token)

            elif token[0] == Tokenizer.TOKEN_NEWLINE:
                break
            else:
                raise ParsingError(token)

        target = Phony(target_name, depends_on, run_after)
        self.__add_target(target)

    def __parse_target(self, it):
        token = it.next()
        EXPECTED_TARGET_NAME_MSG = "expected target name"
        if token[0] == Tokenizer.TOKEN_LITERAL:
            target_type = token[1]

            token = it.next()
            if token[0] == Tokenizer.TOKEN_LITERAL:
                target_name = token[1]
            else:
                raise ParsingError(token, EXPECTED_TARGET_NAME_MSG)
        else:
            raise ParsingError(token, EXPECTED_TARGET_NAME_MSG)

        if target_type == "application":       self.__parse_application_target(target_name, it)
        elif target_type == "static_library":  self.__parse_static_library(target_name, it)
        elif target_type == "phony":           self.__parse_phony(target_name, it)
        else: raise ParsingError(token, "unknown target type: " + target_type)

    def __parse(self):
        it = iter(self.tokens)
        error_msg = "expected set, append or target directive"
        while True:
            try:
                token = it.next()
            except StopIteration:
                debug("eof")
                break

            if token[0] == Tokenizer.TOKEN_LITERAL:
                if token[1] == "set" or token[1] == "append": self.__parse_set_or_append(it, token[1] == "append")
                elif token[1] == "target":                    self.__parse_target(it)
                else: raise ParsingError(token, error_msg)

            elif token[0] == Tokenizer.TOKEN_NEWLINE:
                continue
            else:
                raise ParsingError(token, error_msg)

class Buffer:
    def __init__(self, filename):
        f = open(filename, "r")
        self.position = 0
        self.buf = f.read()
        f.close()

    def value(self):
        if self.eof():
            debug("Read out of range: " + str(self.position))
            raise Exception("eof")

        debug("read: " + str(self.buf[self.position]))
        return str(self.buf[self.position])

    def rewind(self, value = 1):
        self.position = self.position + value

    def seek(self, value):
        self.position = value

    def tell(self):
        return self.position

    def eof(self):
        return self.position >= len(self.buf) or self.position < 0

class Tokenizer:
    TOKEN_OPEN_PARENTHESIS = 1
    TOKEN_CLOSE_PARENTHESIS = 2
    TOKEN_LITERAL = 3
    TOKEN_VARIABLE = 4
    TOKEN_NEWLINE = 5
    TOKEN_MULTILINE_LITERAL = 6

    def __init__(self, filename):
        buf = Buffer(filename)
        self.tokens = []
        self.__tokenize_whitespace(buf)
        debug("tokens: " + str(self.tokens))

    def __is_valid_identifier_char(self, char):
        return char.isalnum() or char in './$_-'

    def __try_add_variable_or_literal(self, token_type, data):
        if len(data) > 0:
            self.__add_token(token_type, data)
        return ""

    def __add_token(self, token_type, content):
        debug("token: " + str(token_type) + "|" + content)
        self.tokens.append((token_type, content))

    def __try_to_read_token(self, buf, what):
        old_position = buf.tell()
        what_position = 0

        while not buf.eof() and what_position < len(what):
            what_char = what[what_position]
            char = buf.value()

            if what_char != char:
                break
            else:
                if what_position == len(what) - 1:
                    buf.rewind()
                    return True

            buf.rewind()
            what_position += 1

        buf.seek(old_position)
        return False

    def __try_tokenize_multiline_literal(self, buf):
        pos = buf.tell()
        data = ''

        if self.__try_to_read_token(buf, '"""'):
            debug("reading multine")
            while True:
                if buf.eof():
                    raise Exception("parse error")

                char = buf.value()

                if self.__try_to_read_token(buf, '"""'):
                    self.__add_token(Tokenizer.TOKEN_MULTILINE_LITERAL, data)
                    return True
                else:
                    data = data + char

                buf.rewind()
        else:
            debug("no multine")
            buf.seek(pos)

        return False

    def __try_tokenize_comment(self, buf):
        if buf.eof():
            return False

        if buf.value() == '#':
            while not buf.eof() and buf.value() != '\n':
                buf.rewind()
            return True
        return False

    def __try_tokenize_simple_chars(self, buf):
        if buf.eof():
            return False

        char = buf.value()

        if char == '\n':
            self.__add_token(Tokenizer.TOKEN_NEWLINE, "<new-line>")
            buf.rewind()
            return True
        elif char == '(':
            self.__add_token(Tokenizer.TOKEN_OPEN_PARENTHESIS, "(")
            buf.rewind()
            return True
        elif char == ')':
            self.__add_token(Tokenizer.TOKEN_CLOSE_PARENTHESIS, ")")
            buf.rewind()
            return True

        return False

    def __try_tokenize_variable_or_literal(self, buf):
        if buf.eof() or not self.__is_valid_identifier_char(buf.value()):
            return False

        if buf.value() == '$':  token_type = Tokenizer.TOKEN_VARIABLE
        else:                   token_type = Tokenizer.TOKEN_LITERAL

        data = ''
        while not buf.eof():
            c = buf.value()
            if self.__is_valid_identifier_char(c):
                data = data + c
                buf.rewind()
            else:
                break

        self.__try_add_variable_or_literal(token_type, data)

        return True

    def __try_tokenize_whitespace(self, buf):
        ret = False
        while not buf.eof() and buf.value() == ' ':
            ret = True
            buf.rewind()

        return ret

    def __tokenize_whitespace(self, buf):
        while not buf.eof():
            ret = (
                self.__try_tokenize_comment(buf) or
                self.__try_tokenize_simple_chars(buf) or
                self.__try_tokenize_variable_or_literal(buf) or
                self.__try_tokenize_whitespace(buf) or
                self.__try_tokenize_multiline_literal(buf)
            )

            if not ret:
                raise Exception("parse error " + str(buf.value()))

            if buf.eof():
                break

class SourceTree:
    def __init__(self):
        self.variable_deposit = VariableDeposit()
        self.files = []
        for filename in self.__find_pake_files():
            self.files.append(PakeFile(self.variable_deposit, filename))

    def build(self, target):
        debug("building " + target)
        found = False
        for f in self.files:
            for t in f.targets:
                if t.name == target:
                    found = True
                    for dependency in t.depends_on:
                        debug(str(t) + " depends on " + dependency)
                        self.build(dependency)
                    t.build()
                    t.after()
        if not found:
            raise Exception("target " + BOLD + target + RESET + " not found in source tree")

    def __find_pake_files(self, path = "."):
        for (dirpath, dirnames, filenames) in os.walk(path):
            for f in filenames:
                filename = dirpath + "/" + f
                (base, ext) = os.path.splitext(filename)
                if ext == ".pake":
                    yield(filename)

def debug(s):
    if "DEBUG" in os.environ:
        print(GRAY + "debug: " + s + RESET)

def info(s):
    print(s)

def main():
    #try:
        target_name = sys.argv[1]
        tree = SourceTree()
        tree.build(target_name)

    #except Exception as e:
    #    print(BOLD_RED + "error: " + RESET + str(e))
    #    sys.exit(1)

main()
