from collections import OrderedDict

from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QFont, QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QPlainTextEdit, QDialog, QFormLayout, QLabel, QLineEdit, QCheckBox, QPushButton, \
    QVBoxLayout, QHBoxLayout, QTreeView, QWidget

from proxycore.parser.http_parser import HttpMessage, HttpRequest, HttpResponse
from proxycore.pipe.reporting import LogReport
from proxycore.utils import soap2python
from proxycore.utils.soap2python import normalize_tag
from proxygui.plugins.abstract_plugins import Plugin, GridPlugin, ContentViewPlugin, SettingsMenuPlugin, TopTabPlugin
from proxygui.plugins.soap.SoapCodeGenerator import SoapCodeGenerator


class SoapPlugin(Plugin, GridPlugin, ContentViewPlugin, SettingsMenuPlugin, TopTabPlugin):
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

    def get_list_tabs(self):
        yield self.soap_code_generator, "SOAP code"

    def soap_code_generator(self, parent):
        return SoapCodeGenerator(self.plugin_registry, self, parent)

    def get_columns(self):
        return (
            ("soap_method", "SOAP method"),
        )

    def get_cell_content(self, data, column_id, value):
        if column_id == "soap_method":
            if not self.is_soap(data.request):
                return "--"

            try:
                method = self.__get_method(data.request)
                return method
            except Exception as ex:
                return str(ex)

    def filter_accepts_row(self, data: LogReport):
        if not self.is_soap(data.request):
            return not self.filter_non_soap_traffic

        method = self.__get_method(data.request)
        return method not in self.filter_methods

    def get_content_representations(self, data: HttpMessage, context: LogReport):
        if self.is_soap(data):
            yield ("SOAP", self.soap_representation)

    def soap_representation(self, data: HttpMessage, context: LogReport, parent_widget):
        body = QPlainTextEdit(parent_widget)
        font = QFont("Courier")
        font.setStyleHint(QFont.Monospace)
        body.setFont(font)

        try:
            soap_text = self.soap_code(data, context)
            body.setPlainText(soap_text)
        except Exception as ex:
            body.setPlainText(str(ex))

        body.setLineWrapMode(QPlainTextEdit.NoWrap)
        body.setReadOnly(True)
        return body

    def soap_code(self, data: HttpMessage, context: LogReport, level=0):
        if isinstance(data, HttpResponse):
            request_element = soap2python.parse_soap_from_string(context.request.body_as_text())
            response_element = soap2python.parse_soap_from_string(context.response.body_as_text())

            soap_text = "    " * level + "@flow.respond_soap("
            soap_text += soap2python.print_method(request_element, "flow.factory", level=level + 1)
            soap_text += "    " * level + ")\n"
            soap_text += "    " * level + "def handle_" + normalize_tag(request_element.tag) + "(self, request):\n"
            soap_text += "    " * level + "    return " + soap2python.print_method(response_element,
                                                                                   "self.flow.factory", level=level + 1)
        else:
            element = soap2python.parse_soap_from_string(data.body_as_text())
            soap_text = soap2python.print_method(element, self.__get_client_for_path(context.request))
        return soap_text

    def is_soap(self, request):
        if request is None:
            return False
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
