from collections import OrderedDict

from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QFont, QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QPlainTextEdit, QDialog, QFormLayout, QLabel, QLineEdit, QCheckBox, QPushButton, \
    QVBoxLayout, QHBoxLayout, QTreeView, QWidget
from proxy.gui.plugins.abstract_plugins import Plugin, GridPlugin, ContentViewPlugin, SettingsMenuPlugin
from proxy.pipe.communication import RequestResponse
from proxy.utils import soap2python

from proxy.parser.http_parser import HttpMessage, HttpRequest


class SoapPlugin(Plugin, GridPlugin, ContentViewPlugin, SettingsMenuPlugin):
    def __init__(self):
        super().__init__("Soap plugin")
        self.filter_non_soap_traffic = True
        self.filter_methods = []
        self.clients_for_paths = OrderedDict()

    @property
    def filter_methods_as_string(self):
        return ",".join(self.filter_methods)

    @filter_methods_as_string.setter
    def filter_methods_as_string(self, methods):
        self.filter_methods = [m.strip() for m in methods.split(",")]

    def get_columns(self):
        return (
            ("soap_method", "SOAP method"),
        )

    def get_cell_content(self, data, column_id, value):
        if column_id == "soap_method":
            if not self.__is_soap(data.request):
                return "--"

            try:
                method = self.__get_method(data.request)
                return method
            except Exception as ex:
                return str(ex)

    def filter_accepts_row(self, data: RequestResponse):
        if not self.__is_soap(data.request):
            return not self.filter_non_soap_traffic

        method = self.__get_method(data.request)
        return method not in self.filter_methods

    def get_content_representations(self, data: HttpMessage, context: RequestResponse):
        if self.__is_soap(data):
            yield ("SOAP", self.soap_representation)

    def soap_representation(self, data: HttpMessage, context: RequestResponse, parent_widget):
        body = QPlainTextEdit(parent_widget)
        font = QFont("Courier")
        font.setStyleHint(QFont.Monospace)
        body.setFont(font)

        try:
            element = soap2python.parse_soap_from_string(data.body_as_text())
            soap_text = soap2python.print_method(element, self.__get_client_for_path(context.request))
            body.setPlainText(soap_text)
        except Exception as ex:
            body.setPlainText(str(ex))

        body.setLineWrapMode(QPlainTextEdit.NoWrap)
        body.setReadOnly(True)
        return body

    def __is_soap(self, request):
        return b"soap" in request.get_content_type() or (
            b"xml" in request.get_content_type() and "schemas.xmlsoap.org" in request.body_as_text())

    def __get_element(self, request):
        element = soap2python.parse_soap_from_string(request.body_as_text())
        return element

    def __get_method(self, request):
        element = self.__get_element(request)
        if "}" in element.tag:
            return element.tag[element.tag.rfind("}") + 1:]
        else:
            return element.tag

    def __get_client_for_path(self, data: HttpRequest):
        for path, client in self.clients_for_paths.items():
            if path.encode() == data.path:
                return client
        return "client"

    def add_settings_menu(self):
        yield "Soap plugin...", self.on_settings_clicked

    def on_settings_clicked(self):
        d = SoapPlugin.SettingsDialog(self)
        if d.exec_():
            self.filter_non_soap_traffic = d.excludeNonSoap.isChecked()
            self.filter_methods_as_string = d.excludeEdit.text()
            self.clients_for_paths = d.client_list.getData()

    def save_settings(self, settings):
        settings.beginGroup("soap_plugin")
        settings.setValue("filter_non_soap_traffic", self.filter_non_soap_traffic)
        settings.setValue("filter_methods", self.filter_methods_as_string)

        settings.beginWriteArray("clients_for_paths")
        i = 0
        for path, client in self.clients_for_paths.items():
            settings.setArrayIndex(i)
            i += 1
            settings.setValue("path", path)
            settings.setValue("client", client)
        settings.endArray()
        settings.endGroup()

    def restore_settings(self, settings: QSettings):
        settings.beginGroup("soap_plugin")
        if settings.value("filter_non_soap_traffic", None):
            self.filter_non_soap_traffic = settings.value("filter_non_soap_traffic") == "true"
        if settings.value("filter_methods", None):
            self.filter_methods_as_string = settings.value("filter_methods")

        size = settings.beginReadArray("clients_for_paths")
        for i in range(size):
            settings.setArrayIndex(i)
            path = settings.value("path")
            client = settings.value("client")
            self.clients_for_paths[path] = client
        settings.endArray()
        settings.endGroup()

    class SettingsDialog(QDialog):
        def __init__(self, plugin):
            super().__init__()

            self.setWindowTitle("Soap plugin settings")

            layout = QVBoxLayout()
            form = QFormLayout()
            self.excludeEdit = QLineEdit()
            self.excludeEdit.setText(plugin.filter_methods_as_string)
            self.excludeNonSoap = QCheckBox()
            self.excludeNonSoap.setChecked(plugin.filter_non_soap_traffic)
            form.addRow(QLabel("Exclude these SOAP messages"), self.excludeEdit)
            form.addRow(QLabel("Exclude non-SOAP traffic"), self.excludeNonSoap)
            layout.addLayout(form)

            layout.addWidget(QLabel("Clients:"))
            self.client_list = SoapPlugin.ClientList(plugin.clients_for_paths)
            layout.addWidget(self.client_list)

            buttons = QHBoxLayout()
            ok = QPushButton("Ok")
            ok.clicked.connect(self.accept)
            cancel = QPushButton("Cancel")
            cancel.clicked.connect(self.close)
            buttons.addWidget(ok)
            buttons.addWidget(cancel)

            layout.addLayout(buttons)

            self.setLayout(layout)

    class ClientList(QWidget):
        def __init__(self, data: ()):
            super().__init__()
            self.tree_view = QTreeView()

            self.model = QStandardItemModel()
            self.rootNode = self.model.invisibleRootItem()
            self.applyModel()

            buttons = QHBoxLayout()
            add = QPushButton("Add")
            add.clicked.connect(self.addClient)
            remove = QPushButton("Remove")
            remove.clicked.connect(self.removeClient)
            buttons.addWidget(add)
            buttons.addWidget(remove)

            layout = QVBoxLayout()
            layout.addLayout(buttons)
            layout.addWidget(self.tree_view)
            self.setLayout(layout)

            if data:
                self.setData(data)

            self.in_progress = False

        def addClient(self):
            branch = [QStandardItem(), QStandardItem()]
            branch[0].setText("/")
            branch[1].setText("client_")
            self.model.appendRow(branch)
            index = self.model.index(self.model.rowCount() - 1, 0)
            self.tree_view.setCurrentIndex(index)
            self.applyModel()

        def removeClient(self):
            index = self.tree_view.currentIndex()
            if index.isValid():
                self.model.removeRow(index.row())
                self.applyModel()

        def applyModel(self):
            self.model.setHeaderData(0, Qt.Horizontal, "Path")
            self.model.setHeaderData(1, Qt.Horizontal, "Client variable")
            self.tree_view.setModel(self.model)

        def getData(self):
            data = {}

            for row in range(self.model.rowCount()):
                path = self.model.data(self.model.index(row, 0))
                client = self.model.data(self.model.index(row, 1))

                if path and client:
                    data[path] = client

            return data

        def setData(self, data):
            for path, client in data.items():
                branch = [QStandardItem(), QStandardItem()]
                branch[0].setText(path)
                branch[1].setText(client)
                self.model.appendRow(branch)
            self.applyModel()


ROLE_PHANTOM_ROW = 1212121
