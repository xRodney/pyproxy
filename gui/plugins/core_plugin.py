from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QPlainTextEdit, QTextEdit, QLabel
from hexdump import hexdump

from gui.plugins.plugin_registry import GridPlugin
from gui.widgets.body_content_viewer import BodyContentViewer
from parser.http_parser import HttpMessage


class CorePlugin(GridPlugin):
    def __init__(self):
        self.plugin_registry = None

    def get_columns(self):
        return (
            ("request", "Request"),
            ("response", "Response")
        )

    def get_cell_content(self, data, column_id, value):
        if column_id == "request":
            msg = data.request
        elif column_id == "response":
            msg = data.response
        else:
            return None

        return msg.first_line().decode().split("\r\n")[0] if msg else "Unmatched"

    def get_tabs(self, rr):
        yield lambda state: self.__build_headers_tab(rr.request, state), "Request head"
        yield lambda state: self.__build_body_tab(rr.request, state), "Request body"
        yield lambda state: self.__build_headers_tab(rr.response, state), "Response head"
        yield lambda state: self.__build_body_tab(rr.response, state), "Response body"

    def get_content_representations(self, data: HttpMessage):
        if data.is_text():
            yield ("Text", self.text_representation)
        if b"text/html" in data.get_content_type():
            yield ("HTML", self.html_representation)
        yield ("Hex", self.hex_representation)

    def text_representation(self, data: HttpMessage, parent_widget):
        body = QPlainTextEdit()
        body.setReadOnly(True)
        body.setPlainText(data.body_as_text())
        return body

    def html_representation(self, data: HttpMessage, parent_widget):
        body = QTextEdit()
        body.setReadOnly(True)
        body.setHtml(data.body_as_text())
        return body

    def hex_representation(self, data: HttpMessage, parent_widget):
        body = QPlainTextEdit()
        font = QFont("Courier")
        font.setStyleHint(QFont.Monospace)
        body.setFont(font)
        body.setPlainText(hexdump(data.body, result="return"))
        body.setLineWrapMode(QPlainTextEdit.NoWrap)
        body.setReadOnly(True)
        return body

    def __build_headers_tab(self, message: HttpMessage, state):
        headers = QTextEdit()
        if message:
            headers_list = (name.decode() + ": " + value.decode() for name, value in message.headers.items())
            headers.setText(message.first_line().decode() + "\n".join(headers_list))
        headers.setReadOnly(True)
        return headers

    def __build_body_tab(self, message: HttpMessage, state):
        if message and message.has_body():
            body = BodyContentViewer(self.plugin_registry, message, state)
        else:
            body = QLabel("No body")
        return body
