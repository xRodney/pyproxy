import os

import suds.sudsobject
from proxy.pipe.recipe.flow import Flow
from proxy.pipe.recipe.soap import soap_transform, SoapFlow, default_response


def register_flow(flow: Flow):
    flow.delegate(NarwhalsService().flow)
    return flow


realpath = os.path.realpath(__file__)
dir = os.path.dirname(realpath)
url = 'file://' + dir + "/Narwhals.wsdl"
client = suds.client.Client(url)
duck_soap_transform = soap_transform(client)


class NarwhalsService:
    flow = SoapFlow(client, "/MSMWebService/WebService.asmx")

    def __init__(self):
        self.counter = 42

    @flow.respond
    def else_response(self, request):
        return default_response(self.flow.client, request)
