from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QTextEdit, QLabel, QPlainTextEdit
from hexdump import hexdump

from gui.widgets.body_content_viewer import BodyContentViewer
from gui.widgets.http_messages_tree_view import ROLE_HTTP_MESSAGE
from parser.http_parser import HttpMessage
from utils import soap2python


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
