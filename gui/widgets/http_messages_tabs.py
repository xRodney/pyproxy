from PyQt5.QtWidgets import QTabWidget


class HttpMessagesTabs(QTabWidget):
    def __init__(self, plugin_registry):
        super().__init__()
        self.plugin_registry = plugin_registry

    def onMessageSelected(self, request_response):
        selected_tab = self.currentIndex()
        self.removeAllTabs()

        for tab, name in self.plugin_registry.get_tabs(request_response):
            self.addTab(tab, name)

        self.setCurrentIndex(selected_tab)

    def removeAllTabs(self):
        while self.count():
            self.removeTab(0)
