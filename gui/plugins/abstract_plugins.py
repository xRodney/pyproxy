from abc import ABCMeta, abstractmethod


class Plugin:
    def __init__(self, name, id=None):
        self.plugin_registry = None
        self.name = name
        self.id = id if id else self.__class__.__name__


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


class SettingsPlugin(metaclass=ABCMeta):
    @abstractmethod
    def add_settings_menu(self):
        pass
