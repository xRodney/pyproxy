from hamcrest.core.matcher import Matcher

from proxy.parser.http_parser import HttpResponse, HttpRequest


class PassThroughMessage:
    def __init__(self, message):
        self.message = message


class RequestResponseMessage():
    def __init__(self, request, response):
        self.messages = request, response


class Transform(object):
    def transform_request(self, request: HttpRequest, proxy: "Proxy") -> HttpRequest:
        return request

    def transform_response(self, response: HttpResponse, proxy: "Proxy") -> HttpResponse:
        return response


class Proxy:
    def __init__(self, parameters, transform: Transform = None, guard=None):
        self.__guard = guard
        self.__transform = transform
        self.__branches = []
        self.parameters = parameters

    def when(self, matcher: Matcher) -> "Proxy":
        proxy = Proxy(self.parameters, guard=matcher)
        self.__branches.append(proxy)
        return proxy

    def transform(self, transform: Transform):
        proxy = Proxy(self.parameters, transform=transform)
        self.__branches.append(proxy)
        return proxy

    def __call__(self, request: HttpRequest):
        if self.__guard and not self.__guard.matches(request):
            return None

        if self.__transform:
            request = self.__transform.transform_request(request, self)

        response = None
        for branch in self.__branches:
            response = branch(request)
            if response:
                break

        if isinstance(response, RequestResponseMessage) and self.__transform:
            response.message = self.__transform.transform_response(response.message, self)

        return response

    def then_respond(self, responder):
        self.__branches.append(lambda request: RequestResponseMessage(request, responder(request)))
        return self

    def then_pass_through(self):
        self.__branches.append(lambda request: PassThroughMessage(request))
        return self
