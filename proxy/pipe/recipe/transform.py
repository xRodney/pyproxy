from hamcrest.core.matcher import Matcher
from typing import Union, Callable, Any

from proxy.parser.http_parser import HttpResponse, HttpRequest
from proxy.pipe.recipe.matchers import LambdaMatcher


class DoesNotAccept(Exception):
    pass


class Transform(object):
    def transform_request(self, request, proxy: "Proxy") -> HttpRequest:
        return request

    def transform_response(self, request, response, original_request, proxy: "Proxy") -> HttpResponse:
        return response


class Proxy:
    def __init__(self, parameters):
        self.__branches = []
        self.parameters = parameters

    def when(self, matcher: Union[Matcher, Callable[[Any], bool]]) -> "Proxy":
        if callable(matcher):
            matcher = LambdaMatcher(matcher)

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
        def _responder(request):
            yield from []  # Needed as the result must be a generator
            response = responder(request)
            return response

        self.__branches.append(_responder)
        return self

    def then_pass_through(self, endpoint="remote"):
        def _responder(request):
            response = yield endpoint, request
            return response

        self.__branches.append(_responder)
        return self

    def then_delegate(self, flow):
        self.__branches.append(flow)
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
        new_request = self.__transform.transform_request(request, self)
        if not new_request:
            raise DoesNotAccept()

        response = yield from super().__call__(new_request)

        response = self.__transform.transform_response(new_request, response, request, self)

        return response
