from PyQt5.QtWidgets import QTabWidget

TAB_CAPTION_PROPERTY = "tab_caption"

class HttpMessagesTabs(QTabWidget):
    def __init__(self, plugin_registry):
        super().__init__()
        self.plugin_registry = plugin_registry

    def onMessageSelected(self, request_response):
        selected_tab = self.currentIndex()
        state = self.saveState()
        self.removeAllTabs()

        for tab_fnc, name in self.plugin_registry.get_tabs(request_response):
            tab_state = state.get(name, None)
            tab = tab_fnc(tab_state)
            tab.setProperty(TAB_CAPTION_PROPERTY, name)
            self.addTab(tab, name)

        self.setCurrentIndex(selected_tab)

    def removeAllTabs(self):
        while self.count():
            self.removeTab(0)
        self.tabs = []

    def saveState(self):
        state = {}
        for i in range(self.count()):
            tab = self.widget(i)
            text = tab.property(TAB_CAPTION_PROPERTY)
            if hasattr(tab, "saveState"):
                state[text] = tab.saveState()
        return state
