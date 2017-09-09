from PyQt5.QtCore import pyqtSignal, QSettings
from PyQt5.QtWidgets import QWidget, QLineEdit, QHBoxLayout

from proxycore.pipe.apipe import ProxyParameters


class ConnectionConfig(QWidget):
    changed = pyqtSignal(ProxyParameters)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.localPortEdit = QLineEdit()
        self.remoteHostEdit = QLineEdit()
        self.remotePortEdit = QLineEdit()

        self.localPortEdit.textChanged.connect(self.onLocalPortChanged)
        self.remoteHostEdit.textChanged.connect(self.onRemoteAddressChanged)
        self.remotePortEdit.textChanged.connect(self.onRemotePortChanged)

        self.localPortEdit.setToolTip("Local port")
        self.localPortEdit.setPlaceholderText("e.g. 8888")
        self.remoteHostEdit.setToolTip("Remote host")
        self.remoteHostEdit.setPlaceholderText("e.g. www.google.com")
        self.remotePortEdit.setToolTip("Remote port")
        self.remotePortEdit.setPlaceholderText("e.g. 80")

        configLayout = QHBoxLayout()
        configLayout.addWidget(self.localPortEdit)
        configLayout.addWidget(self.remoteHostEdit)
        configLayout.addWidget(self.remotePortEdit)

        configLayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(configLayout)

    def onLocalPortChanged(self, text):
        try:
            self.parameters.local_port = int(text)
            self.changed.emit(self.parameters)
        except ValueError:
            pass

    def onLocalAddressChanged(self, text):
        self.parameters.local_address = text
        self.changed.emit(self.parameters)

    def onRemotePortChanged(self, text):
        try:
            self.parameters.remote_port = int(text)
            self.changed.emit(self.parameters)
        except ValueError:
            pass

    def onRemoteAddressChanged(self, text):
        self.parameters.remote_address = text
        self.changed.emit(self.parameters)

    def saveSettings(self, settings: QSettings):
        settings.setValue("local_port", self.parameters.local_port)
        settings.setValue("remote_port", self.parameters.remote_port)
        settings.setValue("remote_host", self.parameters.remote_address)

    def restoreSettings(self, settings: QSettings, defaultParameters):
        self.parameters = defaultParameters
        if settings.value("local_port", None):
            self.parameters.local_port = int(settings.value("local_port"))
        if settings.value("remote_port", None):
            self.parameters.remote_port = int(settings.value("remote_port"))
        if settings.value("remote_host", None):
            self.parameters.remote_address = settings.value("remote_host")

        self.setParameters(self.parameters)
        self.changed.emit(self.parameters)

    def setParameters(self, parameters):
        self.parameters = parameters
        self.localPortEdit.setText(str(self.parameters.local_port))
        self.remoteHostEdit.setText(self.parameters.remote_address)
        self.remotePortEdit.setText(str(self.parameters.remote_port))
