from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox

from parser.http_parser import HttpMessage


class BodyContentViewer(QWidget):
    def __init__(self, plugin_registry, parent=None):
        super().__init__(parent)
        self.plugin_registry = plugin_registry
        vbox = QVBoxLayout()
        self.combo = QComboBox()
        vbox.addWidget(self.combo)
        vbox.addStretch()
        vbox.itemAt(vbox.count() - 1)
        self.vbox = vbox
        self.setLayout(vbox)
        self.combo.currentIndexChanged.connect(self.onComboChanged)

    def setContent(self, data: HttpMessage):
        self.data = data
        self.combo.clear()
        for title, function in self.plugin_registry.get_content_representations(data):
            self.combo.addItem(title, function)

    def onComboChanged(self):
        function = self.combo.currentData()
        if function:
            newWidget = function(self.data, self)
            self.vbox.removeItem(self.vbox.itemAt(self.vbox.count() - 1))
            self.vbox.addWidget(newWidget)
