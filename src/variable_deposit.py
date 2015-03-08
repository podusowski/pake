import os

import ui
import parsing
import fsutils

modules = {}

def export_special_variables(configuration):
    ui.debug("exporting special variables")
    ui.push()

    add_empty("__configuration", "$__null")
    add("__configuration", "$__name", parsing.Token.make_literal(configuration.name))
    for (value, name) in configuration.export:
        add("__configuration", name.content, value)

    for module in modules:
        add(module, "$__build", parsing.Token(parsing.Token.LITERAL, fsutils.build_dir(configuration.name)))

    ui.pop()

def pollute_environment(current_module):
    ui.debug("polluting environment")
    ui.push()
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
    ui.pop()

def eval(current_module, l):
    ui.debug("evaluating " + str(l) + " in context of module " + current_module)
    ui.push()

    ret = []
    for token in l:
        if token.is_a(parsing.Token.LITERAL):
            content = __eval_literal(current_module, token.content)
            ui.debug("  " + token.content + " = " + content)
            ret.append(content)
        elif token.is_a(parsing.Token.VARIABLE):
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

            for value in modules[module][name]:
                if value.is_a(parsing.Token.VARIABLE):
                    re = eval(module, [value])
                    for v in re: ret.append(v)
                else:
                    content = __eval_literal(module, value.content)
                    ret.append(content)
                    ui.debug("    = " + str(content))
        else:
            ui.parse_error(token)

    ui.debug(" = " + str(ret))
    ui.pop()
    return ret

def __eval_literal(current_module, s):
    ui.debug("evaluating literal: " + s)
    ui.push()
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
                evaluated_variable = eval(current_module, [parsing.Token(parsing.Token.VARIABLE, variable_name)])
                ret += " ".join(evaluated_variable)
                variable_name = '$'
                state = STATE_READING
            else:
                variable_name += c
        elif state == STATE_READING_NAME:
            variable_name = variable_name + c

    ui.pop()
    return ret

def add_empty( module_name, name):
    ui.debug("adding empty variable in module " + module_name + " called " + name)

    if not module_name in modules:
        modules[module_name] = {}

    modules[module_name][name] = []


def add(module_name, name, value):
    ui.debug("adding variable in module " + module_name + " called " + name + " with value of " + str(value))

    if not module_name in modules:
        modules[module_name] = {}

    modules[module_name][name] = [value]

def append(module_name, name, value):
    ui.debug("appending variable in module " + module_name + " called " + name + " with value of " + str(value))

    if not module_name in modules:
        modules[module_name] = {}

    if not name in modules[module_name]:
        modules[module_name][name] = []

    modules[module_name][name].append(value)
    ui.debug("  new value: " + str(modules[module_name][name]))

