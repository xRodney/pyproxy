from abc import abstractmethod, ABCMeta

class GridPlugin(metaclass=ABCMeta):
    @abstractmethod
    def get_columns(self):
        pass

    @abstractmethod
    def get_cell_content(self, data, column_id, value):
        pass


class PluginRegistry(GridPlugin):
    def __init__(self):
        self.plugins = []

    def get_columns(self):
        result = []
        for plugin in self.plugins:
            if hasattr(plugin, "get_columns"):
                result += plugin.get_columns()
        return result

    def get_cell_content(self, data, column_id, value=None):
        result = value
        for plugin in self.plugins:
            if hasattr(plugin, "get_cell_content"):
                content = plugin.get_cell_content(data, column_id, result)
                if content:
                    result = content
        return result