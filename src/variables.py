import os

import ui
import lexer
import fsutils

modules = {}

def export_special_variables(configuration):
    ui.debug("exporting special variables")

    with ui.ident:
        add_empty("__configuration", "$__null")

        add("__configuration", "$__name", configuration.name)

        for (value, name) in configuration.export:
            add("__configuration", "".join(name.eval()), value)

        for module in modules:
            add(module, "$__build", fsutils.build_dir(configuration.name))

def pollute_environment(current_module):
    ui.debug("polluting environment")

    with ui.ident:
        for module in modules:
            for (name, variable) in modules[module].iteritems():
                evaluated = eval(module, variable)
                env_name = module + "_" + name[1:]
                os.environ[env_name] = " ".join(evaluated)
                ui.debug("  " + env_name + ": " + str(evaluated))
                if module == current_module:
                    env_short_name = name[1:]
                    os.environ[env_short_name] = " ".join(evaluated)
                    ui.debug("  " + env_short_name + ": " + str(evaluated))


def make_simple_variable(value):
    return Variable(content=value)


class Literal:
    def __init__(self, module, content):
        self.module = module
        self.content = content

    def __str__(self):
        return self.content

    def eval(self):
        s = self.content
        ui.debug("evaluating literal: " + s)

        ret = ""

        STATE_READING = 1
        STATE_WAITING_FOR_PARENTHESIS = 2
        STATE_READING_NAME = 3

        variable_name = '$'
        state = STATE_READING

        for c in s:
            if state == STATE_READING:
                if c == "$":
                    state = STATE_WAITING_FOR_PARENTHESIS
                else:
                    ret += c
            elif state == STATE_WAITING_FOR_PARENTHESIS:
                if c == "{":
                    state = STATE_READING_NAME
                else:
                    ui.parse_error(msg="expecting { after $")
            elif state == STATE_READING_NAME:
                if c == "}":
                    ui.debug("variable: " + variable_name)

                    variable = ReferenceToVariable(self.module, variable_name)
                    ret += " ".join(variable.eval())

                    variable_name = '$'
                    state = STATE_READING
                else:
                    variable_name += c
            elif state == STATE_READING_NAME:
                variable_name = variable_name + c

        return [ret]


class ReferenceToVariable:
    def __init__(self, module, name):
        self.module = module
        self.name = name

    def __str__(self):
        return "${}.{}".format(self.module, self.name)

    __repr__ = __str__

    def eval(self):
        ui.debug("evaluating {!s}".format(self))

        parts = self.name.split(".")

        if len(parts) == 1:
            self.module = self.module
            self.name = parts[0]
        elif len(parts) == 2:
            self.module = parts[0][1:] # lose the $
            self.name = "$" + parts[1]

        global modules

        if not self.module in modules:
            ui.parse_error(msg="no such module: " + module)

        # TODO: make some comment about __configuration variables
        if not self.name in modules[self.module]:
            ui.fatal("{!s} does not exist".format(self))

        return modules[self.module][self.name].eval()


class Variable:
    def __init__(self, module = None, name = None, content = None):
        self.module = module
        self.name = name

        if content:
            self.content = [content]
        else:
            self.content = []

    def __str__(self):
        return "${}.{} = {!s} ".format(self.module, self.name, self.content)

    def eval(self):
        ret = []
        for el in self.content:
            if isinstance(el, str):
                ret += [el]
            else:
                ret += el.eval()

        return ret


def eval(current_module, variable):
    ui.debug("evaluating {!s}, obsolete param current_module: {}".format(variable, current_module))
    ui.push()

    ret = []
    for token in variable.content:
        # TODO: this will eventualy be an polymorphic object
        if isinstance(token, str):
            content = __eval_literal(variable.module, token)
            ui.debug("  " + token + " = " + content)
            ret.append(content)

        elif isinstance(token, Literal) or isinstance(token, ReferenceToVariable) or isinstance(token, Variable):
            ret += token.eval()

        elif token == lexer.Token.LITERAL:
            content = __eval_literal(current_module, token.content)
            ui.debug("  " + token.content + " = " + content)
            ret.append(content)
        elif token == lexer.Token.VARIABLE:
            parts = token.content.split(".")

            ui.debug("dereferencing " + str(parts))

            module = ''
            name = ''
            if len(parts) == 1:
                module = current_module
                name = parts[0]
            elif len(parts) == 2:
                module = parts[0][1:] # lose the $
                name = "$" + parts[1]

            if not module in modules:
                ui.parse_error(msg="no such module: " + module)

            # TODO: make some comment about __configuration variables
            if not name in modules[module]:
                ui.fatal("dereferenced " + name + " but it doesn't exists in module " + module)

            for value in modules[module][name].content:
                ret += eval(module, Variable(content=value))
        else:
            ui.parse_error(token)

    ui.debug(" = " + str(ret))
    ui.pop()
    return ret

def __eval_literal(current_module, s):
    ui.debug("evaluating literal: " + s)

    with ui.ident:
        ret = ""

        STATE_READING = 1
        STATE_WAITING_FOR_PARENTHESIS = 2
        STATE_READING_NAME = 3

        variable_name = '$'
        state = STATE_READING

        for c in s:
            if state == STATE_READING:
                if c == "$":
                    state = STATE_WAITING_FOR_PARENTHESIS
                else:
                    ret += c
            elif state == STATE_WAITING_FOR_PARENTHESIS:
                if c == "{":
                    state = STATE_READING_NAME
                else:
                    ui.parse_error(msg="expecting { after $")
            elif state == STATE_READING_NAME:
                if c == "}":
                    ui.debug("variable: " + variable_name)
                    evaluated_variable = eval(current_module, Variable(content=lexer.Token(lexer.Token.VARIABLE, variable_name)))
                    ret += " ".join(evaluated_variable)
                    variable_name = '$'
                    state = STATE_READING
                else:
                    variable_name += c
            elif state == STATE_READING_NAME:
                variable_name = variable_name + c

        return ret

def add_empty(module_name, name):
    if not module_name in modules:
        modules[module_name] = {}

    variable = Variable(name=name)
    modules[module_name][name] = variable

    ui.debug("adding variable: {!s}".format(variable))


def add(module_name, name, value):
    if not module_name in modules:
        modules[module_name] = {}

    variable = Variable(module_name, name, value)
    modules[module_name][name] = variable

    ui.debug("adding variable: {!s}".format(variable))

def append(module_name, name, value):
    if not module_name in modules:
        modules[module_name] = {}

    if not name in modules[module_name]:
        modules[module_name][name] = Variable(module_name, name)

    variable = modules[module_name][name]
    variable.content.append(value)

    ui.debug("setting variable: {!s}".format(variable))

