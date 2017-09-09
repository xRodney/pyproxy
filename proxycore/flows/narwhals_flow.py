import os

import suds.sudsobject
from proxycore.pipe.recipe.flow import Flow
from proxycore.pipe.recipe.soap import SoapFlow, default_response


def register_flow(flow: Flow):
    flow.delegate(NarwhalsService().flow)
    return flow


realpath = os.path.realpath(__file__)
dir = os.path.dirname(realpath)
url = 'file://' + dir + "/Narwhals.wsdl"
client = suds.client.Client(url)


class NarwhalsService:
    flow = SoapFlow(client, "/narwhals/WebService.asmx")

    def __init__(self):
        self.counter = 42

    @flow.respond
    def else_response(self, request):
        return default_response(self.flow.client, request)
