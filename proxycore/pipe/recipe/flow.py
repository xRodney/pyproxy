import copy
import itertools

from hamcrest.core.matcher import Matcher
from typing import Union, Callable, Any

from proxycore.parser.http_parser import HttpResponse, HttpRequest
from proxycore.pipe.recipe.matchers import LambdaMatcher


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
    def __init__(self, parameters=None):
        self.__branches = []
        self.__fallback = None
        self.__parameters = parameters

    @property
    def parameters(self):
        return self.__parameters

    @parameters.setter
    def parameters(self, parameters):
        self.__parameters = parameters
        for branch in self.__branches:
            if hasattr(branch, "parameters"):
                branch.parameters = parameters

    def __get__(self, instance, owner):
        if not instance:
            return self

        new_flow = instance.__dict__.get("__flow", None)
        if new_flow is not None:
            return new_flow

        new_flow = self._get_branch(instance, owner)

        instance.__dict__["__flow"] = new_flow
        return new_flow

    def _get_branch(self, instance, owner):
        new_flow = copy.copy(self)
        new_flow.__branches = []
        for branch in self.__branches:
            new_flow.__branches.append(self.__bind_branch(branch, instance, owner))

        new_flow.__fallback = self.__bind_branch(self.__fallback, instance, owner)

        return new_flow

    @staticmethod
    def __bind_branch(branch, instance, owner):
        if branch is None:
            return None
        elif hasattr(branch, "_get_branch"):
            return branch._get_branch(instance, owner)
        elif hasattr(branch, "__get__"):
            return branch.__get__(instance, owner)
        else:
            return branch

    def when(self, *matchers: Union[Matcher, Callable[[Any], bool]]) -> "Flow":
        flow = GuardedFlow(matchers, self.__parameters)
        return self.delegate(flow)

    def transform(self, transform: Transform):
        flow = TransformingFlow(transform, self.__parameters)
        return self.delegate(flow)

    def __call__(self, request: HttpRequest):
        excs = []

        fallbacks = (self.__fallback,) if self.__fallback else ()
        for branch in itertools.chain(self.__branches, fallbacks):
            try:
                response = yield from branch(request)
                return response
            except DoesNotAccept as e:
                excs.append(e)

        if not self.__branches and not self.__fallback:
            raise DoesNotAccept("The flow has no branches.")

        raise DoesNotAccept(excs)

    def respond(self, responder):
        """
        Return from the flow with a predefined response.
        :param responder: If callable, it is invoked with the request as an argument (and possibly self if bound).
                        If responder is not callable, it is simply taken as a constant response.
        :return: The responder parameter, unchanged. This allows using this method as a decorator.
        """
        if callable(responder):
            def _responder(*args):
                yield from []  # Needed as the result must be a generator
                response = responder(*args)
                return response
        else:
            def _responder(*args):
                yield from []  # Needed as the result must be a generator
                return responder

        self.__branches.append(_responder)
        return responder

    def call_endpoint(self, endpoint):
        """
        Send the request to an endpoint identified by name. The response that is read from the endpoint will serve
        as the response of the flow.
        :param endpoint: The endpoint name
        """

        def _responder(self, request=None):
            if not request: request = self  # The method can be bound or not bound
            response = yield endpoint, request
            return response

        self.__branches.append(_responder)

    def delegate(self, flow):
        """
        Delegate the flow to another flow. If the delegated flow accepts a request and provides a response,
         it will be treated as a result of this flow.
        :param flow: The flow that will be invoked. It must be a generator.
        :return: The flow parameter. This allows using this method as a decorator.
        """
        self.__branches.append(flow)
        flow.parameters = self.parameters
        return flow

    def fallback(self) -> "Flow":
        """
        Fallback flow is a special delegate flow that is called last, only after all other branches reject the request.
        
        :return: The fallback flow
        """
        if self.__fallback is None:
            self.__fallback = Flow()
            self.__fallback.parameters = self.parameters
        return self.__fallback

    def respond_when(self, *matchers):
        """
        Shortcut to self.when(matcher).respond.
        The purpose of this method is to be used as a decorator.
        
        :param matchers:
        :return: function that, when invoked, will register its parameter as a responder. See #respond.
        """
        return self.when(*matchers).respond


class GuardedFlow(Flow):
    def __init__(self, guards, parameters=None):
        super().__init__(parameters)
        if isinstance(guards, (list, tuple)):
            self.__guards = [self.__convert_matcher(x) for x in guards]
        else:
            self.__guards = (self.__convert_matcher(guards),)

    def __call__(self, request: HttpRequest):
        for g in self.__guards:
            if not g.matches(request):
                raise DoesNotAccept()

        return super().__call__(request)

    @staticmethod
    def __convert_matcher(x):
        return LambdaMatcher(x) if callable(x) else x


class TransformingFlow(Flow):
    def __init__(self, transform, parameters=None):
        super().__init__(parameters)
        self.__transform = transform

    def __call__(self, request: HttpRequest):
        super_call = super().__call__
        return self.__transform.transform(request, self, super_call)
