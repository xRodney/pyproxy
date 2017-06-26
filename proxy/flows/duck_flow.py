import os

import suds
import suds.sudsobject
from proxy.pipe.recipe.matchers import has_path
from proxy.pipe.recipe.soap import soap_transform
from proxy.pipe.recipe.transform import Flow

result = 42


def recipe(flow: Flow):
    realpath = os.path.realpath(__file__)
    dir = os.path.dirname(realpath)
    url = 'file://' + dir + "/DuckService2.wsdl"
    client = suds.client.Client(url)

    soap_flow = flow.when(has_path("/DuckService2")).transform(soap_transform(client))

    @soap_flow.then_respond
    def handle(request):
        response = client.factory.duckAddResponse()
        global result
        setattr(response, "return", result)
        result += 1
        return response
