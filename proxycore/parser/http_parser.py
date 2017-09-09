import gzip
from collections import OrderedDict

from proxycore.parser.parser_utils import get_bytes, get_word, get_rest, get_until

CRLF = "\r\n"


def _force_bytes(msg):
    if msg is None:
        return None
    if isinstance(msg, bytes):
        return msg
    return str(msg).encode()


class HttpMessage:
    def __init__(self, body=None, headers=None):
        self.version = b"HTTP/1.1"
        self.headers = OrderedDict()
        if headers:
            for k, v in headers.items():
                self.headers[_force_bytes(k)] = _force_bytes(v)
        self.body = _force_bytes(body)
        self.__body_as_text = None
        if self.body:
            self.headers.setdefault(b"Content-Length", str(len(self.body)).encode())

    def is_text(self):
        content_type = self.get_content_type()
        return b"text" in content_type or b"xml" in content_type

    def get_content_type(self):
        return self.headers.get(b"Content-Type", b"")

    def get_charset(self):
        """
        Get charset from Content-Encoding header.
        If the header is not present, or it does not contain charset information, None is returned
        :return: Charset of None
        """
        for part in self.get_content_type().split(b";"):
            part = part.strip(b" ").split(b"=")
            if len(part) == 2 and part[0] == b"charset":
                return part[1]

    def __str__(self):
        data = self.first_line().decode()
        for name, value in self.headers.items():
            data += "%s: %s\r\n" % (name.decode(), value.decode())
        data += "\r\n"
        if self.has_body():
            if not self.is_text():
                data += self.body.hex() + "\n"
            else:
                data += str(self.body[:75]) + (self.body[75:] and '... (truncated)')
                data += "\n"

        return data

    def to_bytes(self):
        data = self.first_line()
        yield data
        if self.body and not self.has_body() and b"Content-Length" not in self.headers:
            self.headers[b"Content-Length"] = str(len(self.body)).encode()
        for name, value in self.headers.items():
            yield b"%s: %s\r\n" % (name, value)
        yield b"\r\n"
        if self.has_body():
            yield self.body

    def body_as_text(self):
        if self.__body_as_text:
            return self.__body_as_text
        charset = self.get_charset()
        body = self.body
        if self.headers.get(b"Content-Encoding", b"") == b"gzip":
            body = gzip.decompress(body)
        if charset:
            charset = charset.decode()
            self.__body_as_text = body.decode(charset)
        else:
            try:
                self.__body_as_text = body.decode()
            except UnicodeDecodeError:
                return "Cannot decode"

        return self.__body_as_text

    def has_body(self):
        pass

    def first_line(self):
        pass


class HttpRequest(HttpMessage):
    def __init__(self, method=None, path=None, body=None, headers=None):
        super().__init__(body=body, headers=headers)
        self.method = _force_bytes(method)
        self.path = _force_bytes(path)
        self.__path_query = None

    def has_body(self):
        return self.method in (b"POST", b"PUT", b"PATCH")

    def first_line(self):
        return b"%s %s %s\r\n" % (self.method, self.path, self.version)

    @property
    def path_query(self):
        if self.__path_query is not None:
            return self.__path_query

        self.__path_query = {}

        query = self.path.partition(b"?")
        if not query[2]:
            return self.__path_query

        key_values = query[2].split(b"&")
        for key_value in key_values:
            key, _, value = key_value.partition(b"=")
            if key[-2:] == b"[]":
                key = key[:-2]
                if key in self.__path_query:
                    self.__path_query[key].append(value)
                else:
                    self.__path_query[key] = [value]
            else:
                self.__path_query[key] = value

        return self.__path_query


class HttpResponse(HttpMessage):
    def __init__(self, status=None, status_message=None, body=None, headers=None):
        super().__init__(body=body, headers=headers)
        self.status = _force_bytes(status)
        self.status_message = _force_bytes(status_message)

    @staticmethod
    def ok(body, headers=None):
        return HttpResponse(b"200", b"Ok", body, headers)

    def has_body(self):
        if b"Content-Length" in self.headers:
            return True
        if b"Transfer-Encoding" in self.headers:
            return True

        return self.status in (b"200", b"404")  # TODO: Add all codes that have bodies

    def first_line(self):
        return b"%s %s %s\r\n" % (self.version, self.status, self.status_message)


def get_http_request(data):
    message, data = yield from get_firstline(data)
    message.headers, data = yield from get_headers(data)
    if message.has_body():
        if b"Content-Length" in message.headers:
            message.body, data = yield from get_bytes(data, int(message.headers[b"Content-Length"]))
        elif message.headers.get(b"Transfer-Encoding", None) == b"chunked":
            message.body, data = yield from get_chunked_body(data)
            # TODO: Parse trailing headers
        else:
            message.body, data = yield from get_rest(data)

    return message, data


def get_line(data):
    return get_until(data, b"\r\n")


def parse_http_version(version):
    if version[:5] == b"HTTP/":
        return version
    else:
        return None


def get_firstline(data):
    method, data = yield from get_word(data)
    method = method.upper()
    version = parse_http_version(method)
    if version:
        response = HttpResponse()
        response.version = version
        response.status, data = yield from get_word(data)
        response.status_message, data = yield from get_line(data)

        response.status = response.status
        response.status_message = response.status_message

        return response, data
    else:
        request = HttpRequest()
        request.method = method
        path, data = yield from get_word(data)
        request.path = path
        version_str, data = yield from get_line(data)
        request.version = parse_http_version(version_str)
        return request, data


def get_headers(data):
    headers = OrderedDict()
    line, data = yield from get_line(data)
    name = None
    value = None
    while line:
        if line[0] in (b" ", b"\t") and name:
            # TODO: Double check this logic here, it may leave unwanted characters
            value = value + line
            headers[name] = value
        else:
            parts = line.split(b":", 1)
            if len(parts) == 2:
                headers[parts[0]] = parts[1].lstrip()
            else:
                print(b"Strange header: " + line)
        line, data = yield from get_line(data)

    return headers, data


def get_chunked_body(data):
    chunk_size, data = yield from get_line(data)
    chunk_size = int(chunk_size, 16)
    body = []
    while chunk_size > 0:
        chunk, data = yield from get_bytes(data, int(chunk_size))
        body.append(chunk)
        _, data = yield from get_line(data)  # read the trailing CRLF
        chunk_size, data = yield from get_line(data)
        chunk_size = int(chunk_size, 16)

    assert chunk_size == 0
    _, data = yield from get_line(data)  # read the trailing CRLF

    return b"".join(body), data
