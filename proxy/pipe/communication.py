import collections
import uuid

from proxy.parser.http_parser import HttpRequest, HttpResponse, HttpMessage


class RequestResponse:
    def __init__(self, request=None, response=None):
        self.guid = uuid.uuid4()
        self.response = response
        self.request = request
        self.processing = None

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

        return request_response

    def add_message_pair(self, request, response):
        request_response = RequestResponse(request, response)
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
