from PyQt5.QtWidgets import QTabWidget


class HttpMessagesTabs(QTabWidget):
    def __init__(self, plugin_registry):
        super().__init__()
        self.plugin_registry = plugin_registry
        self.tabs = []

    def onMessageSelected(self, request_response):
        selected_tab = self.currentIndex()
        state = self.saveState()
        self.removeAllTabs()

        for tab, name in self.plugin_registry.get_tabs(request_response):
            self.tabs.append((tab, name))
            self.addTab(tab, name)
            if state.get(name, None) is not None:
                if hasattr(tab, "restoreState"):
                    tab.restoreState(state[name])

        self.setCurrentIndex(selected_tab)

    def removeAllTabs(self):
        while self.count():
            self.removeTab(0)
        self.tabs = []

    def saveState(self):
        state = {}
        for tab, text in self.tabs:
            if hasattr(tab, "saveState"):
                state[text] = tab.saveState()
        return state
