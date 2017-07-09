import sys

from proxy.pipe.apipe import ProxyParameters, ProxyFlowDefinition
from proxy.pipe.reporting import MessageListener

__registered_flow = None


def register_flow(flow):
    global __registered_flow
    __registered_flow = flow
    return flow


def test_definition_loading():
    proxy_parameters = ProxyParameters("localhost", 123, "remotehost", 456)
    this_module = sys.modules[__name__]
    definition = ProxyFlowDefinition(proxy_parameters, this_module, MessageListener())
    flow = definition.get_flow("local")

    assert flow
    assert __registered_flow is flow
