from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox

from proxycore.parser.http_parser import HttpMessage
from proxycore.pipe.reporting import LogReport


class BodyContentViewer(QWidget):
    def __init__(self, plugin_registry, message, context, state, parent=None):
        super().__init__(parent)
        self.plugin_registry = plugin_registry
        vbox = QVBoxLayout()
        self.combo = QComboBox()
        vbox.addWidget(self.combo)
        vbox.addStretch()
        vbox.itemAt(vbox.count() - 1)
        self.vbox = vbox
        self.setLayout(vbox)

        self.setContent(message, context)
        self.restoreState(state)

        self.combo.currentIndexChanged.connect(self.onComboChanged)
        self.onComboChanged()

    def setContent(self, data: HttpMessage, context: LogReport):
        self.data = data
        self.context = context
        self.combo.clear()
        for title, function in self.plugin_registry.get_content_representations(data, context):
            self.combo.addItem(title, function)

    def onComboChanged(self):
        function = self.combo.currentData()
        if function:
            newWidget = function(self.data, self.context, self)
            self.vbox.removeItem(self.vbox.itemAt(self.vbox.count() - 1))
            self.vbox.addWidget(newWidget)

    def saveState(self):
        return dict(selected=self.combo.currentText())

    def restoreState(self, state):
        if state and state.get('selected', None) is not None:
            selected = state['selected']
            for i in range(self.combo.count()):
                if self.combo.itemText(i) == selected:
                    self.combo.setCurrentIndex(i)
                    break
