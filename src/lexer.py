import ui

class FileReader:
    def __init__(self, filename):
        self.line_number = 1

        f = open(filename, "r")
        self.position = 0
        self.buf = f.read()
        f.close()

    def value(self):
        if self.eof():
            ui.debug("Read out of range: " + str(self.position), "TOKENIZER")
            raise Exception("eof")

        ui.debug("read: " + str(self.buf[self.position]), "TOKENIZER")
        return str(self.buf[self.position])

    def rewind(self, value = 1):
        if value > 0:
            for i in xrange(value):
                self.position += 1
                if not self.eof() and self.buf[self.position] == '\n':
                    self.line_number += 1
        elif value < 0:
            for i in xrange(-value):
                self.position -= 1
                if not self.eof() and self.buf[self.position] == '\n':
                    self.line_number -= 1
        else:
            raise Exception("rewind by 0")

    def seek(self, value):
        self.position = value

    def tell(self):
        return self.position

    def eof(self):
        return self.position >= len(self.buf) or self.position < 0


class FileLocation:
    def __init__(self, filename, line, column):
        self.filename = filename
        self.line = line
        self.column = column

    def __str__(self):
        return "{}:{!s}:{!s}".format(self.filename, self.line, self.column)


class Token:
    OPEN_PARENTHESIS = 1
    CLOSE_PARENTHESIS = 2
    LITERAL = 3
    QUOTED_LITERAL = 8
    VARIABLE = 4
    NEWLINE = 5
    MULTILINE_LITERAL = 6
    COLON = 7

    @staticmethod
    def make_literal(content):
        return Token(Token.LITERAL, content)

    def __init__(self, token_type, content, filename=None, line=None, col=None):
        self.token_type = token_type
        self.content = content

        self.filename = filename
        self.line = line
        self.col = col

        self.file_location = FileLocation(filename, line, col)

    def __repr__(self):
        if self.is_a(Token.LITERAL):
            return "literal: " + self.content
        elif self.is_a(Token.VARIABLE):
            return "variable: " + self.content
        else:
            return self.content

    def location_str(self):
        return str(self.file_location)

    def is_a(self, token_type):
        return self.token_type == token_type

    def __eq__(self, other):
        return self.token_type == other

def parse(filename):
    tokenizer = Tokenizer(filename)
    return tokenizer.tokens

class Tokenizer:
    def __init__(self, filename):
        self.filename = filename
        buf = FileReader(filename)
        self.tokens = []
        self.__tokenize(buf)
        ui.debug("tokens: " + str(self.tokens))

    def __is_valid_identifier_char(self, char):
        return char.isalnum() or char in './$_-=+'

    def __try_add_variable_or_literal(self, token_type, data, line):
        if len(data) > 0:
            self.__add_token(token_type, data, line)
        return ""

    def __add_token(self, token_type, content, line = None):
        token = Token(token_type, content, self.filename, line)
        self.tokens.append(token)

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
            ui.debug("reading multine", "TOKENIZER")
            while True:
                if buf.eof():
                    raise Exception("parse error")

                char = buf.value()

                if self.__try_to_read_token(buf, '"""'):
                    self.__add_token(Token.MULTILINE_LITERAL, data, buf.line_number)
                    return True
                else:
                    data = data + char

                buf.rewind()
        else:
            ui.debug("no multine", "TOKENIZER")
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

    def __try_tokenize_slash_newline(self, buf):
        if buf.eof():
            return False

        pos = buf.tell()

        char = buf.value()
        if char == "\\":
            buf.rewind()
            char = buf.value()
            if char == "\n":
                buf.rewind()
                return True
        buf.seek(pos)

        return False

    def __try_tokenize_simple_chars(self, buf):
        if buf.eof():
            return False

        char = buf.value()

        if char == '\n':
            self.__add_token(Token.NEWLINE, "<new-line>", buf.line_number)
            buf.rewind()
            return True
        elif char == '(':
            self.__add_token(Token.OPEN_PARENTHESIS, "(", buf.line_number)
            buf.rewind()
            return True
        elif char == ')':
            self.__add_token(Token.CLOSE_PARENTHESIS, ")", buf.line_number)
            buf.rewind()
            return True
        elif char == ':':
            self.__add_token(Token.COLON, ":", buf.line_number)
            buf.rewind()
            return True

        return False

    def __try_tokenize_variable_or_literal(self, buf):
        if buf.eof() or not self.__is_valid_identifier_char(buf.value()):
            return False

        if buf.value() == '$':  token_type = Token.VARIABLE
        else:                   token_type = Token.LITERAL

        data = ''
        while not buf.eof():
            c = buf.value()
            if self.__is_valid_identifier_char(c):
                data = data + c
                buf.rewind()
            else:
                break

        self.__try_add_variable_or_literal(token_type, data, buf.line_number)

        return True

    def __try_tokenize_quoted_literal(self, buf):
        pos = buf.tell()
        data = ''

        if self.__try_to_read_token(buf, '"'):
           while True:
                if buf.eof():
                    raise Exception("parse error")

                if self.__try_to_read_token(buf, '"'):
                    self.__add_token(Token.QUOTED_LITERAL, data, buf.line_number)
                    return True
                else:
                    char = buf.value()
                    data = data + char

                buf.rewind()
        else:
            buf.seek(pos)

        return False

    def __try_tokenize_whitespace(self, buf):
        ret = False
        while not buf.eof() and buf.value() == ' ':
            ret = True
            buf.rewind()

        return ret

    def __tokenize(self, buf):
        while not buf.eof():
            ret = (
                self.__try_tokenize_comment(buf) or
                self.__try_tokenize_slash_newline(buf) or
                self.__try_tokenize_simple_chars(buf) or
                self.__try_tokenize_quoted_literal(buf) or
                self.__try_tokenize_variable_or_literal(buf) or
                self.__try_tokenize_whitespace(buf) or
                self.__try_tokenize_multiline_literal(buf)
            )

            if not ret:
                ui.parse_error(msg="unexpected character: " + str(buf.value()))

            if buf.eof():
                break


