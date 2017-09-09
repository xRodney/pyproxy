from proxycore.parser.http_parser import HttpMessage
from proxycore.pipe.reporting import LogReport
from proxygui.plugins.abstract_plugins import GridPlugin, ContentViewPlugin, TabPlugin, SettingsMenuPlugin, \
    SettingsPlugin, TopTabPlugin


class PluginRegistry(GridPlugin, ContentViewPlugin, TabPlugin, SettingsMenuPlugin):
    def __init__(self):
        self.__plugins = []
        self.parameters = None

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

    def get_list_tabs(self):
        for plugin in self.__plugins:
            if isinstance(plugin, TopTabPlugin):
                yield from plugin.get_list_tabs()

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

    def filter_accepts_row(self, data: LogReport):
        for plugin in self.__plugins:
            if isinstance(plugin, GridPlugin):
                if not plugin.filter_accepts_row(data):
                    return False
        return True

    def get_content_representations(self, data: HttpMessage, context: LogReport):
        for plugin in self.__plugins:
            if isinstance(plugin, ContentViewPlugin):
                yield from plugin.get_content_representations(data, context)

    def get_tabs(self, data: LogReport):
        for plugin in self.__plugins:
            if isinstance(plugin, TabPlugin):
                yield from plugin.get_tabs(data)

    def add_settings_menu(self):
        for plugin in self.__plugins:
            if isinstance(plugin, SettingsMenuPlugin):
                yield from plugin.add_settings_menu()

    def save_settings(self, settings):
        for plugin in self.__plugins:
            if isinstance(plugin, SettingsPlugin):
                plugin.save_settings(settings)

    def restore_settings(self, settings):
        for plugin in self.__plugins:
            if isinstance(plugin, SettingsPlugin):
                plugin.restore_settings(settings)
