import signal
import sys
import urllib.request
from collections import OrderedDict

from PyQt5.QtCore import QObject, pyqtSignal, QItemSelection, QSettings
from PyQt5.QtGui import QStandardItem, QFont
from PyQt5.QtGui import QStandardItemModel
from PyQt5.QtWidgets import QLineEdit, QLabel, QTextEdit, QComboBox, QPlainTextEdit
from PyQt5.QtWidgets import QTabWidget
from PyQt5.QtWidgets import QTreeView
from PyQt5.QtWidgets import (QWidget, QPushButton,
                             QHBoxLayout, QVBoxLayout, QApplication)
from hexdump import hexdump

from parser.http_parser import HttpMessage
from pipe import apipe
from pipe.communication import RequestResponse, MessageListener
from pipe.persistence import serialize_message_pair, parse_message_pairs
from utils import soap2python

ROLE_HTTP_MESSAGE = 45454
ROLE_HTTP_REQUEST = 45444
ROLE_HTTP_RESPONSE = 45455


class HttpMessagesTreeView(QTreeView):
    selected = pyqtSignal(object)

    class ModelItem:
        def __init__(self, model, branch):
            self.branch = branch
            self.model = model

    def __init__(self, plugins, parent=None):
        super().__init__(parent)
        self.plugins = plugins
        self.clear()
        self.selectionModel().selectionChanged.connect(self.onSelectionChanged)

    def getBranch(self, rr: RequestResponse):
        if rr.guid in self.__index:
            model_item = self.__index[rr.guid]
            branch = model_item.branch
            model_item.model = rr
        else:
            branch = [QStandardItem(), QStandardItem(), QStandardItem()]
            self.rootNode.appendRow(branch)
            self.__index[rr.guid] = HttpMessagesTreeView.ModelItem(rr, branch)

        return branch

    def getAllMessagePairs(self):
        return (item.model for item in self.__index.values())

    def clear(self):
        self.model = QStandardItemModel()
        self.rootNode = self.model.invisibleRootItem()
        self.__index = OrderedDict()
        self.setModel(self.model)

    def applyModel(self):
        self.setModel(self.model)
        column_count = self.model.columnCount()
        column_width = self.width() / column_count
        for col in range(0, column_count):
            self.setColumnWidth(col, column_width)

    def onSelectionChanged(self, selection: QItemSelection):
        if selection.isEmpty():
            return
        item = selection.indexes()[0]
        data = item.data(ROLE_HTTP_MESSAGE)
        if data:
            self.selected.emit(data)


class Worker(QObject, MessageListener):
    received = pyqtSignal(RequestResponse)
    error = pyqtSignal(Exception)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.thread = apipe.PipeThread(self)
        self.local_host = "localhost"
        self.local_port = None
        self.remote_port = None
        self.remote_host = None

    def start(self):
        if not self.thread.is_alive():
            self.thread.start()

        self.thread.start_proxy(self.local_host, int(self.local_port),
                                self.remote_host, int(self.remote_port))

    def stop(self):
        if self.thread.is_alive():
            self.thread.stop_proxy()

    def status(self):
        return self.thread.is_running()

    def on_request_response(self, request_response: RequestResponse):
        self.received.emit(request_response)

    def on_error(self, error):
        if self.thread:
            self.stop()
        self.error.emit(error)

    def save_state(self, settings: QSettings):
        settings.setValue("local_port", self.local_port)
        settings.setValue("remote_port", self.remote_port)
        settings.setValue("remote_host", self.remote_host)

    def restore_state(self, settings: QSettings):
        if settings.value("local_port", None):
            self.local_port = settings.value("local_port")
        if settings.value("remote_port", None):
            self.remote_port = settings.value("remote_port")
        if settings.value("remote_host", None):
            self.remote_host = settings.value("remote_host")


class Example(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = Worker()
        self.plugins = SimpleRequestViewerPlugin()

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

        self.treeView = HttpMessagesTreeView(self.plugins, self)
        self.treeView.selected.connect(self.onMessageSelected)

        self.tabs = QTabWidget(self)

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
        urllib.request.urlopen("http://localhost:" + self.worker.local_port)

    def onSaveClicked(self, event):
        f = open("myfile.dat", "wb")
        for pair in self.treeView.getAllMessagePairs():
            serialize_message_pair(pair, f)
        f.close()

    def onLoadClicked(self, event):
        self.load("TBD")

    def load(self, filename):
        f = open("myfile.dat", "rb")
        for pair in parse_message_pairs(f):
            self.onReceived(pair)
        f.close()

    def closeEvent(self, QCloseEvent):
        if self.worker.status():
            self.worker.stop()

        self.settings.setValue("geometry", self.saveGeometry())
        self.worker.save_state(self.settings)
        super().closeEvent(QCloseEvent)

    def onReceived(self, rr: RequestResponse):
        branch = self.treeView.getBranch(rr)
        self.plugins.on_request_response(rr.request, rr.response, branch)
        self.treeView.applyModel()

    def onError(self, e: Exception):
        self.update_status()

    def onMessageSelected(self, message: HttpMessage):
        self.plugins.on_message_selected(message, self.tabs)

    def update_status(self):
        status = self.worker.status()
        self.startButton.setDisabled(status)
        self.stopButton.setDisabled(not status)
        self.restartButton.setDisabled(not status)
        # self.requestButton.setDisabled(not status)


class SimpleRequestViewerPlugin:
    def get_column_names(self):
        return ("Request", "Response", "Soap method")

    def on_request_response(self, request, response, branch):
        requestNode, responseNode, descriptionNode = branch

        requestNode.setData((request, response), ROLE_HTTP_MESSAGE)

        # branch.removeColumns(0, branch.columnCount())
        request_str = request.first_line().decode().split("\r\n")[0] if request else "Unmatched"
        response_str = response.first_line().decode().split("\r\n")[0] if response else "Unmatched"

        description = self.get_description(request, response)

        requestNode.setText(request_str)
        responseNode.setText(response_str)
        descriptionNode.setText(description)

    def get_description(self, request, response):
        if b"soap" in request.get_content_type() or (
                        b"xml" in request.get_content_type() and "schemas.xmlsoap.org" in request.body_as_text()):
            try:
                element = soap2python.parse_soap_from_string(request.body_as_text())
                return element.tag
            except Exception as ex:
                return str(ex)

        return ""

    def on_message_selected(self, data, tab_view):
        selected_tab = tab_view.currentIndex()
        while tab_view.count():
            tab_view.removeTab(0)

        request, response = data

        tab_view.addTab(self.__build_headers_tab(request), "Request head")
        tab_view.addTab(self.__build_body_tab(request), "Request body")
        tab_view.addTab(self.__build_headers_tab(response), "Response head")
        tab_view.addTab(self.__build_body_tab(response), "Response body")

        tab_view.setCurrentIndex(selected_tab)

    def __build_headers_tab(self, message: HttpMessage):
        headers = QTextEdit()
        if message:
            headers_list = (name.decode() + ": " + value.decode() for name, value in message.headers.items())
            headers.setText(message.first_line().decode() + "\n".join(headers_list))
        headers.setReadOnly(True)
        return headers

    def __build_body_tab(self, message: HttpMessage):
        if message and message.has_body():
            body = BodyContentViewer(self)
            body.setContent(message)
        else:
            body = QLabel("No body")
        return body

    def get_content_representations(self, data: HttpMessage):
        if data.is_text():
            yield ("Text", self.text_representation)
        if b"text/html" in data.get_content_type():
            yield ("HTML", self.html_representation)
        if b"soap" in data.get_content_type() or (
                        b"xml" in data.get_content_type() and "schemas.xmlsoap.org" in data.body_as_text()):
            yield ("SOAP", self.soap_representation)
        yield ("Hex", self.hex_representation)

    def text_representation(self, data: HttpMessage, parent_widget):
        body = QPlainTextEdit(parent_widget)
        body.setReadOnly(True)
        body.setPlainText(data.body_as_text())
        return body

    def html_representation(self, data: HttpMessage, parent_widget):
        body = QTextEdit(parent_widget)
        body.setReadOnly(True)
        body.setHtml(data.body_as_text())
        return body

    def hex_representation(self, data: HttpMessage, parent_widget):
        body = QPlainTextEdit(parent_widget)
        font = QFont("Courier")
        font.setStyleHint(QFont.Monospace)
        body.setFont(font)
        body.setPlainText(hexdump(data.body, result="return"))
        body.setLineWrapMode(QPlainTextEdit.NoWrap)
        body.setReadOnly(True)
        return body

    def soap_representation(self, data: HttpMessage, parent_widget):
        body = QPlainTextEdit(parent_widget)
        font = QFont("Courier")
        font.setStyleHint(QFont.Monospace)
        body.setFont(font)

        try:
            element = soap2python.parse_soap_from_string(data.body_as_text())
            soap_text = soap2python.print_method(element, "client")
            body.setPlainText(soap_text)
        except Exception as ex:
            body.setPlainText(str(ex))

        body.setLineWrapMode(QPlainTextEdit.NoWrap)
        body.setReadOnly(True)
        return body


class BodyContentViewer(QWidget):
    def __init__(self, plugins, parent=None):
        super().__init__(parent)
        self.plugins = plugins
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
        for title, function in self.plugins.get_content_representations(data):
            self.combo.addItem(title, function)

    def onComboChanged(self):
        function = self.combo.currentData()
        if function:
            newWidget = function(self.data, self)
            self.vbox.removeItem(self.vbox.itemAt(self.vbox.count() - 1))
            self.vbox.addWidget(newWidget)


def main():
    app = QApplication(sys.argv)

    # Allow the app to be killed by Ctrl+C (otherwise the Qt window would stay open)
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    ex = Example()
    if len(sys.argv) == 2:
        ex.load(sys.argv[1])
    sys.exit(app.exec_())
