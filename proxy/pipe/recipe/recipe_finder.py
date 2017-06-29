from functools import lru_cache

from proxy.pipe.importing import import_submodules
from proxy.pipe.recipe.flow import Flow


@lru_cache()
def _find_flows():
    import proxy.flows
    modules = import_submodules(proxy.flows)
    prioritized = [(name, mod) for name, mod in modules.items()]
    prioritized.sort(key=lambda tup: tup[0])
    return prioritized


def register_flows(flow: Flow):
    for name, module in _find_flows():
        flow = module.register_flow(flow)
        if flow is None:
            raise ValueError("Function register_flow in module {} must return a flow".format(name))
    return flow
