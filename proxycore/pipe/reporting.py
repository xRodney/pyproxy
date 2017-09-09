import uuid
from collections import OrderedDict

from proxycore.parser.http_parser import HttpMessage, HttpRequest, HttpResponse


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


class MessageListener:
    def on_request_response(self, request_response: RequestResponse):
        pass

    def on_error(self, error):
        print(error)

    def on_change(self, log):
        print(log)

        if "remote" in log.messages:
            merged = RequestResponse(log.messages["remote"].request, log.messages["local"].response)
        else:
            merged = RequestResponse(log.messages["local"].request, log.messages["local"].response)

        merged.guid = log.guid
        self.on_request_response(merged)

class LogReport:
    def __init__(self):
        self.messages = OrderedDict()
        self.guid = uuid.uuid4()

    def log_request(self, endpoint_name, message):
        self.messages.setdefault(endpoint_name, RequestResponse())
        self.messages[endpoint_name].request = message

    def log_response(self, endpoint_name, message):
        self.messages.setdefault(endpoint_name, RequestResponse())
        self.messages[endpoint_name].response = message

    def __str__(self):
        s = "====================================================\n"
        s += "Communication " + str(self.guid) + "\n"
        for name, rr in self.messages.items():
            s += self.__str1(name, rr)
        s += "====================================================\n"
        return s

    def __str1(self, name: str, rr: RequestResponse):
        s = ""
        if rr.request:
            s += name + " REQUEST:\n"
            s += str(rr.request) + "\n"

        if rr.response:
            s += name + " RESPONSE:\n"
            s += str(rr.response) + "\n"

        return s

    @property
    def request(self):
        if "remote" in self.messages:
            return self.messages["remote"].request
        else:
            return self.messages["local"].request

    @property
    def response(self):
        return self.messages["local"].response