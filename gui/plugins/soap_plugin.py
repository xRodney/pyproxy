from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QPlainTextEdit, QDialog, QFormLayout, QLabel, QLineEdit, QCheckBox

from gui.plugins.abstract_plugins import Plugin, GridPlugin, ContentViewPlugin, SettingsPlugin
from parser.http_parser import HttpMessage
from utils import soap2python


class SoapPlugin(Plugin, GridPlugin, ContentViewPlugin, SettingsPlugin):
    def __init__(self):
        super().__init__("Soap plugin")

    def get_columns(self):
        return (
            ("soap_method", "SOAP method"),
        )

    def get_cell_content(self, data, column_id, value):
        if column_id == "soap_method":
            if not self.__is_soap(data.request):
                return "--"

            try:
                element = self.__get_element(data.request)
                return element.tag
            except Exception as ex:
                return str(ex)

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

    def add_settings_menu(self):
        yield "Soap plugin...", self.on_settings_clicked

    def on_settings_clicked(self):
        d = QDialog()
        d.setWindowTitle("Soap plugin settings")

        layout = QFormLayout()
        excludeEdit = QLineEdit()
        excludeNonSoap = QCheckBox()
        layout.addRow(QLabel("Exclude these SOAP messages"), excludeEdit)
        layout.addRow(QLabel("Exclude non-SOAP traffic"), excludeNonSoap)

        d.setLayout(layout)

        d.exec_()
