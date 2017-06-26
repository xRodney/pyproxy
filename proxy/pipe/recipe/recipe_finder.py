from functools import lru_cache

from proxy.pipe.importing import import_submodules
from proxy.pipe.recipe.transform import Flow


@lru_cache()
def _find_flows():
    import proxy.flows
    return import_submodules(proxy.flows)


def register_flows(flow: Flow):
    for name, module in _find_flows().items():
        flow = module.register_flow(flow)
        if flow is None:
            raise ValueError("Function register_flow in module {} must return a flow".format(name))
    return flow
