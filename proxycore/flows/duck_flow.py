import os

import suds.sudsobject
from proxycore.parser.http_parser import HttpResponse
from proxycore.pipe.recipe.flow import Flow
from proxycore.pipe.recipe.soap import soap_transform, SoapFlow


def register_flow(flow: Flow):
    flow.delegate(DuckService().flow)
    flow.delegate(DuckService3().flow)
    return flow


realpath = os.path.realpath(__file__)
dir = os.path.dirname(realpath)
url = 'file://' + dir + "/DuckService2.wsdl"
client = suds.client.Client(url)
duck_soap_transform = soap_transform(client)


class DuckService:
    flow = SoapFlow(client, "/DuckService2")

    def __init__(self):
        self.counter = 42

    @flow.respond_soap(flow.factory.duckAdd(
        username=r"?",
        password=r"?",
        settings=flow.factory(
            key=r"?",
            value=r"?"
        )
    )
    )
    def handle_duckAdd(self, request):
        return self.flow.factory.duckAddResponse(
            result=115
        )

    @flow.respond_soap(flow.factory.duckAdd())
    def duck_add(self, request):
        response = self.flow.factory.duckAddResponse(result=self.counter)
        self.counter += 1
        return response

    @flow.respond
    def else_response(self, request):
        return HttpResponse(b"500",
                            b"Unmatched request",
                            b"The proxy is unable to mock the request")


class DuckService3:
    flow = SoapFlow(client, "/DuckService3")

    def __init__(self):
        self.counter = 15

    @flow.respond_soap(flow.factory.duckAdd())
    def duck_add(self, request):
        response = self.flow.factory.duckAddResponse(result=self.counter)
        self.counter += 1
        return response

    @flow.respond
    def else_response(self, request):
        return HttpResponse(b"500",
                            b"Unmatched request",
                            b"The proxy is unable to mock the request")
