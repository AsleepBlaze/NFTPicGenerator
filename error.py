# -*- encoding: utf-8 -*-

class BaseError(Exception):
    def __init__(self, message='', code=None):
        self.message = message
        self.code = code

    def __str__(self):
        return self.message if self.code is None else '%s (%d)' % (self.message, self.code)
