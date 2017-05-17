import urllib.request

from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QWidget, QLineEdit, QHBoxLayout, QPushButton, QVBoxLayout, QMessageBox, \
    QFileDialog

from gui.plugins import PLUGINS
from gui.plugins.plugin_registry import PluginRegistry
from gui.widgets.http_messages_tabs import HttpMessagesTabs
from gui.widgets.http_messages_tree_view import HttpMessagesTreeView
from gui.worker import Worker
from parser.http_parser import HttpMessage
from pipe.communication import RequestResponse
from pipe.persistence import parse_message_pairs, serialize_message_pairs


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = Worker()
        self.plugin_registry = PluginRegistry()
        self.plugin_registry.plugins = PLUGINS

        self.setGeometry(300, 300, 750, 750)
        self.setWindowTitle('PyProxy')

        self.settings = QSettings("MyCompany", "MyApp")
        if self.settings.value("geometry", None):
            self.restoreGeometry(self.settings.value("geometry"))
        self.worker.restore_state(self.settings)

        self.initUI()

    def initUI(self):

        localPortEdit = QLineEdit()
        remoteHostEdit = QLineEdit()
        remotePortEdit = QLineEdit()

        localPortEdit.textChanged.connect(lambda text: setattr(self.worker, 'local_port', text))
        remoteHostEdit.textChanged.connect(lambda text: setattr(self.worker, 'remote_host', text))
        remotePortEdit.textChanged.connect(lambda text: setattr(self.worker, 'remote_port', text))

        localPortEdit.setText(self.worker.local_port if self.worker.local_port else "8001")
        remoteHostEdit.setText(self.worker.remote_host if self.worker.remote_host else "www.httpwatch.com")
        remotePortEdit.setText(self.worker.remote_port if self.worker.remote_port else "80")

        configLayout = QHBoxLayout()
        configLayout.addWidget(localPortEdit)
        configLayout.addWidget(remoteHostEdit)
        configLayout.addWidget(remotePortEdit)

        self.startButton = QPushButton("Start")
        self.stopButton = QPushButton("Stop")
        self.restartButton = QPushButton("Restart")
        self.requestButton = QPushButton("Request")
        self.saveButton = QPushButton("Save")
        self.loadButton = QPushButton("Load")

        self.startButton.clicked.connect(self.onStartClicked)
        self.stopButton.clicked.connect(self.onStopClicked)
        self.restartButton.clicked.connect(self.onRestartClicked)
        self.requestButton.clicked.connect(self.onRequestClicked)
        self.saveButton.clicked.connect(self.onSaveClicked)
        self.loadButton.clicked.connect(self.onLoadClicked)
        self.worker.received.connect(self.onReceived)
        self.worker.error.connect(self.onError)

        hbox = QHBoxLayout()
        hbox.addWidget(self.startButton)
        hbox.addWidget(self.stopButton)
        hbox.addWidget(self.restartButton)
        hbox.addWidget(self.requestButton)
        hbox.addWidget(self.saveButton)
        hbox.addWidget(self.loadButton)

        self.treeView = HttpMessagesTreeView(self.plugin_registry, self)
        self.treeView.selected.connect(self.onMessageSelected)

        self.tabs = HttpMessagesTabs(self.plugin_registry)

        vbox = QVBoxLayout()
        vbox.addLayout(configLayout)
        vbox.addLayout(hbox)
        vbox.addWidget(self.treeView)
        vbox.addWidget(self.tabs)

        self.setLayout(vbox)

        self.show()

        self.update_status()

    def onStartClicked(self, event):
        self.worker.start()
        self.update_status()

    def onStopClicked(self, event):
        self.worker.stop()
        self.update_status()

    def onRestartClicked(self, event):
        self.worker.stop()
        self.treeView.clear()
        self.worker.start()
        self.update_status()

    def onRequestClicked(self):
        try:
            urllib.request.urlopen("http://localhost:" + self.worker.local_port)
        except Exception as e:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("The request resulted in an error:")
            msg.setInformativeText(str(e))
            msg.setWindowTitle("Error")
            msg.exec_()

    def onSaveClicked(self, event):
        file_name = QFileDialog.getSaveFileName(self, 'Save HTTP messages', '.', filter='*.http')[0]
        if not file_name:
            return

        if not file_name.endswith(".http"):
            file_name += ".http"

        self.save(file_name)


    def onLoadClicked(self, event):
        file_name = QFileDialog.getOpenFileName(self, 'Save HTTP messages', '.', filter='*.http')[0]
        if file_name:
            self.load(file_name)

    def load(self, file_name):
        f = open(file_name, "rb")
        for pair in parse_message_pairs(f):
            self.onReceived(pair)
        f.close()

    def save(self, file_name):
        f = open(file_name, "wb")
        serialize_message_pairs(self.treeView.getAllMessagePairs(), f)
        f.close()

    def closeEvent(self, QCloseEvent):
        if self.worker.status():
            self.worker.stop()

        self.settings.setValue("geometry", self.saveGeometry())
        self.worker.save_state(self.settings)
        super().closeEvent(QCloseEvent)

    def onReceived(self, rr: RequestResponse):
        self.treeView.onRequestResponse(rr)

    def onError(self, e: Exception):
        self.update_status()
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText("There was an error:")
        msg.setInformativeText(str(e))
        msg.setWindowTitle("Error")
        msg.exec_()

    def onMessageSelected(self, message: HttpMessage):
        self.tabs.onMessageSelected(message)

    def update_status(self):
        status = self.worker.status()
        self.startButton.setDisabled(status)
        self.stopButton.setDisabled(not status)
        self.restartButton.setDisabled(not status)
        # self.requestButton.setDisabled(not status)
