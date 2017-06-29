import os

import suds.sudsobject
from proxy.parser.http_parser import HttpResponse
from proxy.pipe.recipe.flow import Flow
from proxy.pipe.recipe.matchers import has_path
from proxy.pipe.recipe.soap import soap_transform, soap_matches_loosely


def register_flow(flow: Flow):
    duck_flow = flow.when(has_path("/DuckService2"))
    duck_flow.then_delegate(DuckService().flow)
    duck_flow.then_respond(lambda request: HttpResponse(b"500",
                                                        b"Unmatched request",
                                                        b"The proxy is unable to mock the request"))

    return flow


realpath = os.path.realpath(__file__)
dir = os.path.dirname(realpath)
url = 'file://' + dir + "/DuckService2.wsdl"
client = suds.client.Client(url)
duck_soap_transform = soap_transform(client)


class DuckService:
    flow = Flow().transform(duck_soap_transform)

    def __init__(self):
        self.counter = 42

    @flow.respond_when(soap_matches_loosely(
        client.factory.duckAdd())
    )
    def duck_add(self, request):
        response = client.factory.duckAddResponse()
        setattr(response, "return", self.counter)
        self.counter += 1
        return response
