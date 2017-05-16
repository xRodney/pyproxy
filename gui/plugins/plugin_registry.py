from abc import abstractmethod, ABCMeta

from parser.http_parser import HttpMessage
from pipe.communication import RequestResponse


class GridPlugin(metaclass=ABCMeta):
    @abstractmethod
    def get_columns(self):
        pass

    @abstractmethod
    def get_cell_content(self, data, column_id, value):
        pass


class ContentViewPlugin(metaclass=ABCMeta):
    @abstractmethod
    def get_content_representations(self, data):
        pass


class TabPlugin(metaclass=ABCMeta):
    @abstractmethod
    def get_tabs(self, data):
        pass


class PluginRegistry(GridPlugin, ContentViewPlugin, TabPlugin):
    def __init__(self):
        self.__plugins = []

    @property
    def plugins(self):
        return self.__plugins

    @plugins.setter
    def plugins(self, plugins):
        for p in plugins:
            self.add_plugin(p)

    def add_plugin(self, plugin):
        plugin.plugin_registry = self
        self.__plugins.append(plugin)

    def get_columns(self):
        result = []
        for plugin in self.__plugins:
            if hasattr(plugin, "get_columns"):
                result += plugin.get_columns()
        return result

    def get_cell_content(self, data, column_id, value=None):
        result = value
        for plugin in self.__plugins:
            if hasattr(plugin, "get_cell_content"):
                content = plugin.get_cell_content(data, column_id, result)
                if content:
                    result = content
        return result

    def get_content_representations(self, data: HttpMessage):
        for plugin in self.__plugins:
            if hasattr(plugin, "get_content_representations"):
                yield from plugin.get_content_representations(data)

    def get_tabs(self, data: RequestResponse):
        for plugin in self.__plugins:
            if hasattr(plugin, "get_tabs"):
                yield from plugin.get_tabs(data)
