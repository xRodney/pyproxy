from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QPlainTextEdit, QDialog, QFormLayout, QLabel, QLineEdit, QCheckBox, QPushButton, \
    QVBoxLayout, QHBoxLayout

from gui.plugins.abstract_plugins import Plugin, GridPlugin, ContentViewPlugin, SettingsPlugin
from parser.http_parser import HttpMessage
from pipe.communication import RequestResponse
from utils import soap2python


class SoapPlugin(Plugin, GridPlugin, ContentViewPlugin, SettingsPlugin):
    def __init__(self):
        super().__init__("Soap plugin")
        self.filter_non_soap_traffic = True
        self.filter_methods = []

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



    def get_content_representations(self, data: HttpMessage):
        if self.__is_soap(data):
            yield ("SOAP", self.soap_representation)

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


    def add_settings_menu(self):
        yield "Soap plugin...", self.on_settings_clicked

    def on_settings_clicked(self):
        d = SoapPlugin.SettingsDialog(self)
        if d.exec_():
            self.filter_non_soap_traffic = d.excludeNonSoap.isChecked()
            self.filter_methods_as_string = d.excludeEdit.text()

    def save_settings(self, settings):
        settings.setValue("filter_non_soap_traffic", self.filter_non_soap_traffic)
        settings.setValue("filter_methods", self.filter_methods_as_string)

    def restore_settings(self, settings):
        if settings.value("filter_non_soap_traffic", None):
            self.filter_non_soap_traffic = bool(settings.value("filter_non_soap_traffic"))
        if settings.value("filter_methods", None):
            self.filter_methods_as_string = settings.value("filter_methods")

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

            buttons = QHBoxLayout()
            ok = QPushButton("Ok")
            ok.clicked.connect(self.accept)
            cancel = QPushButton("Cancel")
            cancel.clicked.connect(self.close)
            buttons.addWidget(ok)
            buttons.addWidget(cancel)

            layout.addLayout(buttons)

            self.setLayout(layout)
