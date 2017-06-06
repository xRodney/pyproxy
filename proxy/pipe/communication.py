import collections
import uuid

from proxy.parser.http_parser import HttpRequest, HttpResponse, HttpMessage


class RequestResponse:
    def __init__(self, request=None, response=None):
        self.guid = uuid.uuid4()
        self.response = response
        self.request = request

    def __str__(self):
        s = "====================================================\n"
        s += "Communication " + str(self.guid) + "\n"
        s += "REQUEST:\n"
        s += str(self.request) + "\n"
        s += "RESPONSE:\n"
        s += str(self.response) + "\n"
        s += "====================================================\n"
        return s

    def set_request_or_response(self, message: HttpMessage):
        if isinstance(message, HttpRequest):
            self.request = message
        elif isinstance(message, HttpResponse):
            self.response = message
        else:
            raise ValueError("Message must be either request or response")


class MessageProcessor:
    def __init__(self, proxy_parameters):
        self.remote_port = proxy_parameters.remote_port
        self.remote_address = proxy_parameters.remote_address
        self.local_port = proxy_parameters.local_port
        self.local_address = proxy_parameters.local_address

    def __get_address(self, address, port=None):
        if port:
            return b"%s:%s" % (str(address).encode(), str(port).encode())
        else:
            return b"%s" % (str(address).encode())

    def local_address_with_port(self):
        return self.__get_address(self.local_address, self.local_port)

    def remote_address_with_port(self):
        return self.__get_address(self.remote_address, self.remote_port)

    def local_address_without_port(self):
        return self.__get_address(self.local_address)

    def remote_address_without_port(self):
        return self.__get_address(self.remote_address)

    def replace_local_with_remote(self, input: bytes):
        s = input
        s = s.replace(self.local_address_with_port(), self.remote_address_with_port())
        s = s.replace(self.local_address_without_port(), self.remote_address_without_port())
        return s

    def replace_remote_with_local(self, input: bytes):
        s = input
        s = s.replace(self.remote_address_with_port(), self.local_address_with_port())
        s = s.replace(self.remote_address_without_port(), self.local_address_without_port())
        return s

    def replace_local_with_remote_in_header(self, msg, header):
        if msg.headers.get(header):
            msg.headers[header] = self.replace_local_with_remote(msg.headers[header])

    def replace_remote_with_local_in_header(self, msg, header):
        if msg.headers.get(header):
            msg.headers[header] = self.replace_remote_with_local(msg.headers[header])

    def process_message(self, msg):
        self.replace_local_with_remote_in_header(msg, b"Host")
        self.replace_local_with_remote_in_header(msg, b"Referer")
        self.replace_remote_with_local_in_header(msg, b"Location")

        if msg.headers.get(b"Transfer-Encoding", "") == b"chunked":
            del msg.headers[b"Transfer-Encoding"]
            msg.headers[b"Content-Length"] = str(len(msg.body)).encode()

        return msg


class MessagePairer:
    def __init__(self, listener=None):
        self.pending = collections.deque()
        self.last_class_in_pending = None
        self.listener = listener

    def add_message(self, message: HttpMessage):
        if not isinstance(message, (HttpRequest, HttpResponse)):
            raise Exception("Message must be either request or response")

        if len(self.pending) == 0 or self.last_class_in_pending is message.__class__:
            self.last_class_in_pending = message.__class__
            request_response = RequestResponse()
            self.pending.append(request_response)
        else:
            request_response = self.pending.popleft()

        request_response.set_request_or_response(message)
        self.have_request_response(request_response)

    def add_request(self, request: HttpRequest):
        self.add_message(request)

    def add_response(self, response: HttpResponse):
        self.add_message(response)

    def have_request_response(self, request_response):
        if self.listener:
            self.listener.on_request_response(request_response)


class MessageListener:
    def on_request_response(self, request_response: RequestResponse):
        print(request_response)

    def on_error(self, error):
        print(error)
