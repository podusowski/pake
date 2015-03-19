import ui
import lexer
import command_line
import fsutils
import variables

configurations = {}

def build_dir():
    return fsutils.build_dir(get_selected_configuration().name)

def application_suffix():
    return " ".join(variables.eval("", get_selected_configuration().application_suffix))

def compiler():
    return " ".join(variables.eval("", get_selected_configuration().compiler))

def compiler_flags():
    return " ".join(variables.eval("", get_selected_configuration().compiler_flags))

def linker_flags():
    return " ".join(variables.eval("", get_selected_configuration().linker_flags))

def archiver():
    return " ".join(variables.eval("", get_selected_configuration().archiver))

def application_suffix():
    return " ".join(variables.eval("", get_selected_configuration().application_suffix))

def get_selected_configuration():
    return configurations[command_line.args.configuration]

def add_configuration(configuration):
    ui.debug("adding configuration: " + str(configuration))
    configurations[configuration.name] = configuration

def _create_default_configuration():
    configuration = Configuration()
    add_configuration(configuration)

class Configuration:
    def __init__(self):
        self.name = "__default"
        self.compiler = variables.make_simple_variable("c++")
        self.compiler_flags = variables.make_simple_variable("-I.")
        self.linker_flags = variables.make_simple_variable("-L.")
        self.application_suffix = variables.make_simple_variable("")
        self.archiver = variables.make_simple_variable("ar")
        self.export = []

    def __repr__(self):
        return self.name

_create_default_configuration()

