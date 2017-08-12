from collections import OrderedDict

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QTabWidget

TAB_CAPTION_PROPERTY = "tab_caption"


class TopTabs(QTabWidget):
    selected = pyqtSignal(object)

    def __init__(self, plugin_registry, parent=None):
        super().__init__(parent)
        self.plugin_registry = plugin_registry
        self.tabs = []
        self.messages = OrderedDict()

        for tab_fnc, name in self.plugin_registry.get_list_tabs():
            tab = tab_fnc(self)
            tab.setProperty(TAB_CAPTION_PROPERTY, name)
            if hasattr(tab, "selected"):
                tab.selected.connect(self.onMessageSelected)
            self.addTab(tab, name)
            self.tabs.append(tab)

    def removeAllTabs(self):
        while self.count():
            self.removeTab(0)
        self.tabs = []

    def onMessageSelected(self, message):
        self.selected.emit(message)

    def onLogChange(self, log):
        is_new = log.guid not in self.messages
        self.messages[log.guid] = log

        for tab in self.tabs:
            if hasattr(tab, "onLogChange"):
                tab.onLogChange(log, is_new, self.messages)

    def clear(self):
        self.__log_index = OrderedDict()
        for tab in self.tabs:
            if hasattr(tab, "clear"):
                tab.clear()

    def refresh(self):
        for tab in self.tabs:
            if hasattr(tab, "refresh"):
                tab.refresh()

    def getAllMessagePairs(self):
        return self.messages.values()
