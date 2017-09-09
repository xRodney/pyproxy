# Adapted from StackOverflow:
# https://stackoverflow.com/questions/3365740/how-to-import-all-submodules
# https://stackoverflow.com/a/25562415

import importlib
import pkgutil

import sys


def import_submodules(package, recursive=True):
    """ Import all submodules of a module, recursively, including subpackages

    :param package: package (name or actual module)
    :type package: str | module
    :rtype: dict[str, types.ModuleType]
    """
    if isinstance(package, str):
        package = import_module(package)

    if not hasattr(package, "__path__"):  # "Package" is in fact just a module
        return {package.__name__: package}

    results = {}
    for loader, name, is_pkg in pkgutil.walk_packages(package.__path__):
        full_name = package.__name__ + '.' + name
        results[full_name] = import_module(full_name)
        if recursive and is_pkg:
            results.update(import_submodules(full_name))
    return results


def import_module(name):
    if name in sys.modules.keys():
        importlib.reload(sys.modules[name])
        return sys.modules[name]
    else:
        return importlib.import_module(name)