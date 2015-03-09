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
        self.compiler = [lexer.Token.make_literal("c++")]
        self.compiler_flags = [lexer.Token.make_literal("-I.")]
        self.linker_flags = [lexer.Token.make_literal("-L.")]
        self.application_suffix = [lexer.Token.make_literal("")]
        self.archiver = [lexer.Token.make_literal("ar")]
        self.export = []

    def __repr__(self):
        return self.name

_create_default_configuration()

