from hamcrest.core.matcher import Matcher

from proxy.parser.http_parser import HttpResponse, HttpRequest


async def write_message(msg, writer):
    for data in msg.to_bytes():
        writer.write(data)
    await writer.drain()


class PassThroughMessage:
    def __init__(self, request):
        self.request = request


class RequestResponseMessage():
    def __init__(self, request, response):
        self.request = request
        self.response = response


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
                response = yield from branch(request)
                return response
            except DoesNotAccept:
                pass

        raise DoesNotAccept()

    def then_respond(self, responder):
        self.__branches.append(PredefinedResponder(responder))
        return self

    def then_pass_through(self):
        self.__branches.append(PassThroughResponder())
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


class PassThroughResponder:
    def __call__(self, request):
        response = yield PassThroughMessage(request)
        return response


class PredefinedResponder:
    def __init__(self, responder):
        self.responder = responder

    def __call__(self, request):
        response = self.responder(request)
        result = yield RequestResponseMessage(request, response)
        return result


class OngoingProcessing:
    def __init__(self, processor, msg):
        self.processing = processor(msg)
        self.__state = 0

    def get_processing_message(self):
        self.__state += 1
        assert self.__state == 1, "get_request_message must be called first"
        return self.processing.send(None)

    def have_response(self, response):
        self.__state += 1
        assert self.__state == 2, "have_response must be called second"
        try:
            self.processing.send(response)
            assert False, "Processing pipeline must yield exactly once"
        except StopIteration as e:
            return e.value
