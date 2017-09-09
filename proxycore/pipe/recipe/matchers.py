from hamcrest.core.base_matcher import BaseMatcher

from proxycore.parser.http_parser import HttpMessage, HttpRequest


class HasHeader(BaseMatcher):
    def __init__(self, header, *values):
        self.header = header
        self.values = values

    def _matches(self, message: HttpMessage):
        if self.header not in message.headers:
            return False

        if self.values:
            return self.header[self.header] in self.values
        else:
            return True


def has_header(header, *values):
    return HasHeader(header, values)


def has_content_type(*content_types):
    return HasHeader(b"Content-Type", content_types)


class HasMethod(BaseMatcher):
    def __init__(self, method):
        self.method = method

    def _matches(self, message: HttpRequest):
        if not isinstance(message, HttpRequest):
            return False

        return message.method == self.method


def has_path(path):
    return HasPath(path)


class HasPath(BaseMatcher):
    def __init__(self, path):
        self.path = path
        if isinstance(self.path, str):
            self.path = self.path.encode()

    def _matches(self, message: HttpRequest):
        if not isinstance(message, HttpRequest):
            return False

        return message.path == self.path


def has_path_starting(path):
    return HasPathStarting(path)


class HasPathStarting(BaseMatcher):
    def __init__(self, path):
        self.path = path
        if isinstance(self.path, str):
            self.path = self.path.encode()

    def _matches(self, message: HttpRequest):
        if not isinstance(message, HttpRequest):
            return False

        return message.path[:len(self.path)] == self.path


def has_method(method):
    return HasMethod(method)


class LambdaMatcher(BaseMatcher):
    def __init__(self, predicate):
        self.predicate = predicate

    def _matches(self, obj):
        return self.predicate(obj)
