from gui.plugins.abstract_plugins import GridPlugin, ContentViewPlugin, TabPlugin, SettingsPlugin
from parser.http_parser import HttpMessage
from pipe.communication import RequestResponse


class PluginRegistry(GridPlugin, ContentViewPlugin, TabPlugin, SettingsPlugin):
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
            if isinstance(plugin, GridPlugin):
                result += plugin.get_columns()
        return result

    def get_cell_content(self, data, column_id, value=None):
        result = value
        for plugin in self.__plugins:
            if isinstance(plugin, GridPlugin):
                content = plugin.get_cell_content(data, column_id, result)
                if content:
                    result = content
        return result

    def get_content_representations(self, data: HttpMessage):
        for plugin in self.__plugins:
            if isinstance(plugin, ContentViewPlugin):
                yield from plugin.get_content_representations(data)

    def get_tabs(self, data: RequestResponse):
        for plugin in self.__plugins:
            if isinstance(plugin, TabPlugin):
                yield from plugin.get_tabs(data)

    def add_settings_menu(self):
        for plugin in self.__plugins:
            if isinstance(plugin, SettingsPlugin):
                yield from plugin.add_settings_menu()
