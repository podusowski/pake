import ui
import lexer
import command_line

configurations = {}

def get_selected_configuration():
    return get_configuration(command_line.args.configuration)

def get_configuration(configuration_name):
    return configurations[configuration_name]

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

_create_default_configuration()

