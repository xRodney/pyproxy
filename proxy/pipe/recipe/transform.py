from hamcrest.core.matcher import Matcher

from proxy.parser.http_parser import HttpResponse, HttpRequest


class PassThroughMessage:
    def __init__(self, message):
        self.message = message


class RequestResponseMessage():
    def __init__(self, request, response):
        self.messages = request, response


class DoesNotAccept(Exception):
    pass


class Transform(object):
    def transform_request(self, request: HttpRequest, proxy: "Proxy") -> HttpRequest:
        return request

    def transform_response(self, response: HttpResponse, proxy: "Proxy") -> HttpResponse:
        return response


class Proxy:
    def __init__(self, parameters):
        self.__branches = []
        self.parameters = parameters

    def when(self, matcher: Matcher) -> "Proxy":
        proxy = GuardedProxy(self.parameters, matcher)
        self.__branches.append(proxy)
        return proxy

    def transform(self, transform: Transform):
        proxy = TransformingProxy(self.parameters, transform)
        self.__branches.append(proxy)
        return proxy

    def __call__(self, request: HttpRequest):

        for branch in self.__branches:
            try:
                response = branch(request)
                return response
            except DoesNotAccept:
                pass

        raise DoesNotAccept()

    def then_respond(self, responder):
        self.__branches.append(lambda request: RequestResponseMessage(request, responder(request)))
        return self

    def then_pass_through(self):
        self.__branches.append(lambda request: PassThroughMessage(request))
        return self


class GuardedProxy(Proxy):
    def __init__(self, parameters, guard):
        super().__init__(parameters)
        self.__guard = guard

    def __call__(self, request: HttpRequest):
        if not self.__guard.matches(request):
            raise DoesNotAccept()

        return super().__call__(request)


class TransformingProxy(Proxy):
    def __init__(self, parameters, transform):
        super().__init__(parameters)
        self.__transform = transform

    def __call__(self, request: HttpRequest):
        request = self.__transform.transform_request(request, self)
        if not request:
            raise DoesNotAccept()

        response = super().__call__(request)

        if isinstance(response, RequestResponseMessage):
            response.message = self.__transform.transform_response(response.message, self)

        return response
