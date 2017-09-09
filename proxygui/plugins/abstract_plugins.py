from abc import ABCMeta, abstractmethod

from proxycore.pipe.reporting import LogReport


class Plugin:
    def __init__(self, name, id=None):
        self.plugin_registry = None
        self.name = name
        self.id = id if id else self.__class__.__name__


class GridPlugin(metaclass=ABCMeta):
    def get_columns(self):
        return ()

    def get_cell_content(self, data, column_id, value):
        return None

    def filter_accepts_row(self, data: LogReport):
        return True


class ContentViewPlugin(metaclass=ABCMeta):
    @abstractmethod
    def get_content_representations(self, data, context: LogReport):
        pass


class TopTabPlugin(metaclass=ABCMeta):
    @abstractmethod
    def get_list_tabs(self):
        pass

class TabPlugin(metaclass=ABCMeta):
    @abstractmethod
    def get_tabs(self, data):
        pass


class SettingsPlugin(metaclass=ABCMeta):
    def save_settings(self, settings):
        pass

    def restore_settings(self, settings):
        pass


class SettingsMenuPlugin(SettingsPlugin):
    @abstractmethod
    def add_settings_menu(self):
        pass
