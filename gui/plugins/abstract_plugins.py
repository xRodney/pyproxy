from abc import ABCMeta, abstractmethod

from pipe.communication import RequestResponse


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

    def filter_accepts_row(self, data: RequestResponse):
        return True


class ContentViewPlugin(metaclass=ABCMeta):
    @abstractmethod
    def get_content_representations(self, data, context: RequestResponse):
        pass


class TabPlugin(metaclass=ABCMeta):
    @abstractmethod
    def get_tabs(self, data):
        pass


class SettingsPlugin(metaclass=ABCMeta):
    @abstractmethod
    def add_settings_menu(self):
        pass

    def save_settings(self, settings):
        pass

    def restore_settings(self, settings):
        pass
