import os

import ui
import lexer
import targets
import variables
import configurations

from variables import Variable

def parse(filename):
    Module(filename)

class CommonTargetParameters:
    def __init__(self, root_path, module_name, name):
        assert isinstance(module_name, str)
        assert isinstance(name, str)

        self.root_path = root_path
        self.module_name = module_name
        self.name = name
        self.artefacts = Variable()
        self.prerequisites = Variable()
        self.depends_on = Variable()
        self.run_before = Variable()
        self.run_after = Variable()
        self.resources = Variable()
        self.visible_in = Variable()

class CxxParameters:
    def __init__(self):
        self.sources = Variable()
        self.include_dirs = Variable()
        self.compiler_flags = Variable()
        self.built_targets = Variable()

class Module:
    def __init__(self, filename):
        assert isinstance(filename, str)

        ui.debug("parsing " + filename)

        with ui.ident:
            self.filename = filename
            self.name = self.__get_module_name(filename)

            self.tokens = lexer.parse(filename)

            self.__parse()

            variables.add(
                self.name,
                "$__path",
                lexer.Token.make_literal(os.path.dirname(filename)))

            variables.add_empty(
                self.name,
                "$__null")

    def __get_module_name(self, filename):
        base = os.path.basename(filename)
        (root, ext) = os.path.splitext(base)
        return root


    def __parse_set_or_append(self, it, append):

        def token_to_variable(token):
            if token == lexer.Token.LITERAL:
                return variables.Literal(self.name, token.content)
            elif token == lexer.Token.VARIABLE:
                return variables.ReferenceToVariable(self.name, token.content)

        token = it.next()
        if token == lexer.Token.VARIABLE:
            variable_name = token.content
        else:
            ui.parse_error(token)

        second_add = False
        while True:
            token = it.next()
            if token in [lexer.Token.LITERAL, lexer.Token.VARIABLE]:
                if append or second_add:
                    variables.append(self.name, variable_name, token_to_variable(token))
                else:
                    variables.add(self.name, variable_name, token_to_variable(token))
                    second_add = True

            elif token == lexer.Token.NEWLINE:
                break
            else:
                ui.parse_error(token)

    # (something1 something2)
    def __parse_list(self, it):
        ret = variables.Variable()
        token = it.next()
        if token == lexer.Token.OPEN_PARENTHESIS:

            while True:
                token = it.next()
                if token == lexer.Token.LITERAL:
                    ret.content.append(variables.Literal(module=self.name, content=token.content))
                elif token == lexer.Token.VARIABLE:
                    ret.content.append(variables.ReferenceToVariable(module=self.name, name=token.content))
                elif token == lexer.Token.CLOSE_PARENTHESIS:
                    break
                else:
                    ui.parse_error(token)
        else:
            ui.parse_error(token)

        return ret

    # ($var1:$var2 something4:$var1)
    def __parse_colon_list(self, it):
        ret = []
        token = it.next()
        if token == lexer.Token.OPEN_PARENTHESIS:

            while True:
                token = it.next()

                first = None
                second = None

                if token in [lexer.Token.LITERAL, lexer.Token.VARIABLE]:
                    first = token
                    token = it.next()
                    if token == lexer.Token.COLON:
                        token = it.next()
                        if token == lexer.Token.VARIABLE:
                            second = token
                            ret.append((first, second))
                        else:
                            ui.parse_error(token, msg="expected variable")
                    else:
                        ui.parse_error(token, msg="expected colon")
                elif token == lexer.Token.CLOSE_PARENTHESIS:
                    break
                else:
                    ui.parse_error(token)
        else:
            ui.parse_error(token)

        ui.debug("colon list: " + str(ret))
        return ret

    def __try_parse_target_common_parameters(self, common_parameters, token, it):
        if token.content == "depends_on":
            common_parameters.depends_on = self.__parse_list(it)
            return True
        elif token.content == "run_before":
            common_parameters.run_before = self.__parse_list(it)
            return True
        elif token.content == "run_after":
            common_parameters.run_after = self.__parse_list(it)
            return True
        elif token.content == "resources":
            common_parameters.resources = self.__parse_list(it)
            return True
        elif token.content == "visible_in":
            common_parameters.visible_in = self.__parse_list(it)
            return True

        return False

    def __try_parse_cxx_parameters(self, cxx_parameters, token, it):
        if token.content == "sources":
            cxx_parameters.sources = self.__parse_list(it)
            return True
        elif token.content == "include_dirs":
            cxx_parameters.include_dirs = self.__parse_list(it)
            return True
        elif token.content == "compiler_flags":
            cxx_parameters.compiler_flags = self.__parse_list(it)
            return True

        return False

    def __parse_application_target(self, target_name, it):
        link_with = variables.Variable()
        library_dirs = variables.Variable()

        common_parameters = CommonTargetParameters(
            os.path.dirname(self.filename),
            self.name,
            target_name)

        cxx_parameters = CxxParameters()

        while True:
            token = it.next()
            if token == lexer.Token.LITERAL:
                if self.__try_parse_target_common_parameters(common_parameters, token, it): pass
                elif self.__try_parse_cxx_parameters(cxx_parameters, token, it): pass
                elif token.content == "link_with": link_with = self.__parse_list(it)
                elif token.content == "library_dirs": library_dirs = self.__parse_list(it)
                else: ui.parse_error(token)
            elif token == lexer.Token.NEWLINE:
                break
            else:
                ui.parse_error(token)

        target = targets.Application(common_parameters, cxx_parameters, link_with, library_dirs)
        targets.add_target(target)

    def __parse_static_library(self, target_name, it):
        common_parameters = CommonTargetParameters(
            os.path.dirname(self.filename),
            self.name,
            target_name)

        cxx_parameters = CxxParameters()

        while True:
            token = it.next()
            if token == lexer.Token.LITERAL:
                if self.__try_parse_target_common_parameters(common_parameters, token, it): pass
                elif self.__try_parse_cxx_parameters(cxx_parameters, token, it): pass
                else: ui.parse_error(token)
            elif token == lexer.Token.NEWLINE:
                break
            else:
                ui.parse_error(token)

        target = targets.StaticLibrary(common_parameters, cxx_parameters)
        targets.add_target(target)

    def __parse_phony(self, target_name, it):
        common_parameters = CommonTargetParameters(
            os.path.dirname(self.filename),
            self.name,
            target_name)

        cxx_parameters = CxxParameters()

        while True:
            token = it.next()
            if token == lexer.Token.LITERAL:
                if self.__try_parse_target_common_parameters(common_parameters, token, it): pass
                elif token.content == "artefacts": common_parameters.artefacts = self.__parse_list(it)
                elif token.content == "prerequisites": common_parameters.prerequisites = self.__parse_list(it)
                else: ui.parse_error(token)

            elif token == lexer.Token.NEWLINE:
                break
            else:
                ui.parse_error(token)

        target = targets.Phony(common_parameters)
        targets.add_target(target)

    def __parse_target(self, it):
        token = it.next()
        if token == lexer.Token.LITERAL:
            target_type = token.content

            token = it.next()
            if token == lexer.Token.LITERAL:
                target_name = token.content
            else:
                ui.parse_error(token)
        else:
            ui.parse_error(token)

        if target_type == "application":       self.__parse_application_target(target_name, it)
        elif target_type == "static_library":  self.__parse_static_library(target_name, it)
        elif target_type == "phony":           self.__parse_phony(target_name, it)
        else: ui.parse_error(token, msg="unknown target type: " + target_type)

    def __parse_configuration(self, it):
        configuration = configurations.Configuration()

        # name
        token = it.next()
        if token == lexer.Token.LITERAL:
            configuration.name = token.content
        else:
            ui.parse_error(token)

        while True:
            token = it.next()
            if token == lexer.Token.LITERAL:
                if token.content == "compiler": configuration.compiler = self.__parse_list(it)
                elif token.content == "archiver": configuration.archiver = self.__parse_list(it)
                elif token.content == "application_suffix": configuration.application_suffix = self.__parse_list(it)
                elif token.content == "compiler_flags": configuration.compiler_flags = self.__parse_list(it)
                elif token.content == "linker_flags": configuration.linker_flags = self.__parse_list(it)
                elif token.content == "export": configuration.export = self.__parse_colon_list(it)
                else: ui.parse_error(token)

            elif token == lexer.Token.NEWLINE:
                break
            else:
                ui.parse_error(token)

        ui.debug("configuration parsed:" + str(configuration))
        configurations.add_configuration(configuration)

    def __parse_directive(self, it):
        while True:
            token = it.next()

            if token == lexer.Token.LITERAL:
                if token.content == "set" or token.content == "append": self.__parse_set_or_append(it, token.content == "append")
                elif token.content == "target":                    self.__parse_target(it)
                elif token.content == "configuration":             self.__parse_configuration(it)
                else: ui.parse_error(token, msg="expected directive")

            elif token == lexer.Token.NEWLINE:
                continue
            else:
                return False

    def __parse(self):
        it = iter(self.tokens)

        try:
            if not self.__parse_directive(it):
                ui.parse_error(msg="unknown :(")
        except StopIteration:
            ui.debug("eof")

