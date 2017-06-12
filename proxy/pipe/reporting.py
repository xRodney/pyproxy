import uuid

from proxy.parser.http_parser import HttpMessage, HttpRequest, HttpResponse


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


class MessageListener:
    def on_request_response(self, request_response: RequestResponse):
        pass

    def on_error(self, error):
        print(error)

    def on_any_message(self, log):
        for endpoint, rr in log.items():
            print("====== {} =====".format(endpoint))
            print(rr)

        if "remote" in log:
            merged = RequestResponse(log["remote"].request, log["local"].response)
        else:
            merged = RequestResponse(log["local"].request, log["local"].response)

        merged.guid = log["local"].guid
        self.on_request_response(merged)
