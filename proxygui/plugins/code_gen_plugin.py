from PyQt5.QtWidgets import QTextEdit

from proxycore.parser.http_parser import HttpMessage, HttpRequest, HttpResponse
from proxycore.pipe.reporting import LogReport
from proxygui.plugins.abstract_plugins import Plugin, ContentViewPlugin


class CodeGenPlugin(Plugin, ContentViewPlugin):
    def __init__(self):
        super().__init__("Code generator plugin")

    def get_content_representations(self, data, context: LogReport):
        yield "Python code", self.python_code_representation

    def python_code_representation(self, data: HttpMessage, context, parent_widget):
        body = QTextEdit()
        body.setReadOnly(True)

        if isinstance(data, HttpRequest):
            text = "HttpRequest({}, {}".format(data.method, data.path)
        elif isinstance(data, HttpResponse):
            text = "HttpResponse({}, {}".format(data.status, data.status_message)
        else:
            text = "???("

        if data.headers:
            text += ",\n"
            text += "\theaders={\n"
            for header, value in data.headers.items():
                text += "\t\t{}: {},\n".format(header, value)
            text += "\t}"

        if data.has_body():
            text += ",\n"
            text += "\tbody={}".format(data.body)

        text += "\n)"

        body.setText(text)
        return body
