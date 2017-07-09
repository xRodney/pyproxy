from functools import lru_cache

from proxy.pipe.importing import import_submodules
from proxy.pipe.recipe.flow import Flow


@lru_cache()
def _find_flows(module):
    modules = import_submodules(module)
    prioritized = [(name, mod) for name, mod in modules.items()]
    prioritized.sort(key=lambda tup: tup[0])
    return prioritized


def register_flows(module, flow: Flow):
    for name, module in _find_flows(module):
        try:
            flow = module.register_flow(flow)
        except Exception as e:
            raise Exception("There was an error registering flow: ", e)

        if flow is None:
            raise ValueError("Function register_flow in module {} must return a flow".format(name))
    return flow
