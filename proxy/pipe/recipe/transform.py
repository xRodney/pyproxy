from hamcrest.core.matcher import Matcher
from typing import Union, Callable, Any

from proxy.parser.http_parser import HttpResponse, HttpRequest
from proxy.pipe.recipe.matchers import LambdaMatcher


class DoesNotAccept(Exception):
    pass


class Transform(object):
    def transform_request(self, request, proxy: "Flow") -> HttpRequest:
        return request

    def transform_response(self, request, response, original_request, proxy: "Flow") -> HttpResponse:
        return response

    def transform(self, request, proxy: "Flow", next_in_chain):
        new_request = self.transform_request(request, proxy)
        if not new_request:
            raise DoesNotAccept()

        response = yield from next_in_chain(new_request)

        response = self.transform_response(new_request, response, request, proxy)

        return response


class Flow:
    def __init__(self, bind_to=None):
        self.__branches = []
        self.__parameters = None
        self.bind_to = bind_to

    @property
    def parameters(self):
        return self.__parameters

    @parameters.setter
    def parameters(self, parameters):
        self.__parameters = parameters
        for branch in self.__branches:
            branch.parameters = parameters

    def when(self, matcher: Union[Matcher, Callable[[Any], bool]]) -> "Flow":
        if callable(matcher):
            matcher = LambdaMatcher(matcher)

        flow = GuardedFlow(self.bind_to, matcher)
        return self.then_delegate(flow)

    def transform(self, transform: Transform):
        flow = TransformingFlow(self.bind_to, transform)
        return self.then_delegate(flow)

    def __call__(self, request: HttpRequest, bind_to=None):
        if bind_to is None:
            bind_to = self.bind_to

        for branch in self.__branches:
            try:
                response = yield from branch(request, bind_to)
                return response
            except DoesNotAccept:
                pass

        raise DoesNotAccept()

    def then_respond(self, responder):
        def _responder(request, bind_to):
            yield from []  # Needed as the result must be a generator
            if bind_to:
                response = responder(bind_to, request)
            else:
                response = responder(request)
            return response

        self.__branches.append(_responder)
        return self

    def then_pass_through(self, endpoint="remote"):
        def _responder(request, bind_to):
            response = yield endpoint, request
            return response

        self.__branches.append(_responder)
        return self

    def then_delegate(self, flow):
        self.__branches.append(flow)
        flow.parameters = self.parameters
        return flow

    def respond_when(self, matcher):
        return self.when(matcher).then_respond

    def handle_by(self, handler_class):
        handler = handler_class()
        flow = handler.flow
        flow.bind_to = handler
        self.then_delegate(flow)



class GuardedFlow(Flow):
    def __init__(self, parameters, guard):
        super().__init__(parameters)
        self.__guard = guard

    def __call__(self, request: HttpRequest, bind_to=None):
        if not self.__guard.matches(request):
            raise DoesNotAccept()

        return super().__call__(request, bind_to)


class TransformingFlow(Flow):
    def __init__(self, parameters, transform):
        super().__init__(parameters)
        self.__transform = transform

    def __call__(self, request: HttpRequest, bind_to=None):
        super_call = super().__call__
        return self.__transform.transform(request, self, lambda request: super_call(request, bind_to))
