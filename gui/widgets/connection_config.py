from PyQt5.QtCore import pyqtSignal, QSettings
from PyQt5.QtWidgets import QWidget, QLineEdit, QHBoxLayout

from pipe.apipe import ProxyParameters


class ConnectionConfig(QWidget):
    changed = pyqtSignal(ProxyParameters)

    def __init__(self, parameters: ProxyParameters, parent=None):
        super().__init__(parent)

        self.parameters = parameters

        localPortEdit = QLineEdit()
        remoteHostEdit = QLineEdit()
        remotePortEdit = QLineEdit()

        localPortEdit.textChanged.connect(self.onLocalPortChanged)
        remoteHostEdit.textChanged.connect(self.onRemoteAddressChanged)
        remotePortEdit.textChanged.connect(self.onRemotePortChanged)

        localPortEdit.setText(str(self.parameters.local_port))
        remoteHostEdit.setText(self.parameters.remote_address)
        remotePortEdit.setText(str(self.parameters.remote_port))

        configLayout = QHBoxLayout()
        configLayout.addWidget(localPortEdit)
        configLayout.addWidget(remoteHostEdit)
        configLayout.addWidget(remotePortEdit)

        configLayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(configLayout)

    def onLocalPortChanged(self, text):
        self.parameters.local_port = int(text)
        self.changed.emit(self.parameters)

    def onLocalAddressChanged(self, text):
        self.parameters.local_address = text
        self.changed.emit(self.parameters)

    def onRemotePortChanged(self, text):
        self.parameters.remote_port = int(text)
        self.changed.emit(self.parameters)

    def onRemoteAddressChanged(self, text):
        self.parameters.remote_address = text
        self.changed.emit(self.parameters)

    def saveSettings(self, settings: QSettings):
        settings.setValue("local_port", self.parameters.local_port)
        settings.setValue("remote_port", self.parameters.remote_port)
        settings.setValue("remote_host", self.parameters.remote_address)

    def restoreSettings(self, settings: QSettings):
        if settings.value("local_port", None):
            self.parameters.local_port = int(settings.value("local_port"))
        if settings.value("remote_port", None):
            self.parameters.remote_port = int(settings.value("remote_port"))
        if settings.value("remote_host", None):
            self.parameters.remote_address = settings.value("remote_host")

        self.changed.emit(self.parameters)
