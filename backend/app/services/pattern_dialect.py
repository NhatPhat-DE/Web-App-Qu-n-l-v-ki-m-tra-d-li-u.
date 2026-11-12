"""Positive recursive-descent grammar for the deliberately small re2-v1 dialect.
No matching or Python re fallback lives here.
"""
import json


class PatternSyntaxError(ValueError):
    pass


class Parser:
    def __init__(self, text):
        self.text, self.pos = text, 0

    def peek(self):
        return self.text[self.pos:self.pos + 1]

    def expression(self):
        self.sequence()
        while self.peek() == '|':
            self.pos += 1
            self.sequence()

    def sequence(self):
        while self.peek() and self.peek() not in ')|':
            repeatable = self.atom()
            if self.peek() and self.peek() in '*+?{':
                if not repeatable:
                    raise PatternSyntaxError('Anchors cannot be repeated.')
                self.quantifier()
                if self.peek() and self.peek() in '*+?{':
                    raise PatternSyntaxError('Stacked/lazy/possessive quantifiers are outside re2-v1.')

    def escaped(self, in_class=False):
        self.pos += 1
        char = self.peek()
        if not char:
            raise PatternSyntaxError('Incomplete escape.')
        self.pos += 1
        if char in 'dws':
            return None
        controls = {'n': '\n', 'r': '\r', 't': '\t', 'f': '\f', 'v': '\v'}
        if char in controls:
            return controls[char]
        # Only explicit regex punctuation may be escaped; no octal/hex/property/backref.
        if char in r'\.^$|?*+()[]{}-':
            return char
        raise PatternSyntaxError('Unsupported escape.')

    def class_char(self):
        if self.peek() == chr(92):
            return self.escaped(True)
        char = self.peek()
        if not char or char in '[]':
            raise PatternSyntaxError('Invalid class item; escape literal brackets.')
        self.pos += 1
        return char

    def character_class(self):
        self.pos += 1
        if self.peek() == '^':
            self.pos += 1
        count = 0
        while self.peek() and self.peek() != ']':
            left = self.class_char()
            count += 1
            if self.peek() == '-' and self.text[self.pos + 1:self.pos + 2] not in ('', ']'):
                self.pos += 1
                right = self.class_char()
                if left is None or right is None or ord(left) > ord(right):
                    raise PatternSyntaxError('Range endpoints must be ordered literal code points.')
        if not count or self.peek() != ']':
            raise PatternSyntaxError('Empty or unclosed character class.')
        self.pos += 1

    def atom(self):
        char = self.peek()
        if char == '(':
            self.pos += 1
            if self.peek() == '?':
                raise PatternSyntaxError('Only ordinary groups are allowed.')
            self.expression()
            if self.peek() != ')':
                raise PatternSyntaxError('Unclosed group.')
            self.pos += 1
            return True
        if char == '[':
            self.character_class()
            return True
        if char == chr(92):
            self.escaped()
            return True
        if char in '*+?{}]':
            raise PatternSyntaxError('Unexpected metacharacter; escape literals.')
        self.pos += 1
        return char not in '^$'

    def quantifier(self):
        char = self.peek()
        self.pos += 1
        if char != '{':
            return
        def number():
            start = self.pos
            while self.peek() and '0' <= self.peek() <= '9':
                self.pos += 1
            value = self.text[start:self.pos]
            if not value or len(value) > 4 or int(value) > 1000 or len(value) > 1 and value[0] == '0':
                raise PatternSyntaxError('Count must be canonical ASCII 0..1000.')
            return int(value)
        lower = number()
        if self.peek() == ',':
            self.pos += 1
            upper = None if self.peek() == '}' else number()
            if upper is not None and upper < lower:
                raise PatternSyntaxError('Reversed repetition bounds.')
        if self.peek() != '}':
            raise PatternSyntaxError('Invalid counted repetition.')
        self.pos += 1


def validate_config(config):
    if not isinstance(config, dict) or set(config) != {'pattern', 'dialect'}:
        raise PatternSyntaxError('Config must contain exactly pattern and dialect.')
    pattern = config['pattern']
    if not isinstance(pattern, str) or not isinstance(config['dialect'], str) or config['dialect'] != 're2-v1':
        raise PatternSyntaxError('pattern must be a string and dialect must be re2-v1.')
    try:
        if not 1 <= len(pattern) <= 512 or len(pattern.encode('utf-8')) > 2048:
            raise PatternSyntaxError('Pattern exceeds 1..512 code points / 2048 UTF-8 bytes.')
        if len(json.dumps(config, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')) > 16384:
            raise PatternSyntaxError('Config exceeds 16 KiB.')
    except UnicodeError:
        raise PatternSyntaxError('Pattern must be valid UTF-8.') from None
    if chr(0) in pattern:
        raise PatternSyntaxError('NUL is outside re2-v1.')
    parser = Parser(pattern)
    parser.expression()
    if parser.pos != len(pattern):
        raise PatternSyntaxError('Unexpected closing group.')
    return pattern
