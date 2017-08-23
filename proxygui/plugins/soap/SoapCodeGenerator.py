import re
from collections import OrderedDict

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QPlainTextEdit


class SoapCodeGenerator(QPlainTextEdit):
    selected = pyqtSignal(object)

    def __init__(self, plugin_registry, soap_plugin, parent=None):
        super().__init__(parent)
        self.plugin_registry = plugin_registry
        self.soap_plugin = soap_plugin
        self.clear()

        font = QFont("Courier")
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setReadOnly(True)

    def clear(self):
        self.setPlainText("")
        self.__index_by_path = OrderedDict()
        self.__index_by_position = {}

    def refresh(self):
        pass

    def onLogChange(self, log, is_new, all_messages):
        if log.request is not None and log.response is not None and self.soap_plugin.is_soap(log.response):
            snippet = self.soap_plugin.soap_code(log.response, log, level=1) + "\n"

            start, old_length = self.__get_start_and_old_length(log, len(snippet))
            self.__replace_text(start, old_length, snippet)

    def __get_start_and_old_length(self, log, new_length):
        path = log.request.path.decode()
        guid = log.guid

        if path in self.__index_by_path:
            index = self.__index_by_path[path]
            if guid in index:
                # The log record already exists -> return cached values
                old_length = index[guid][1]
                start = index[guid][0]
                index[guid] = start, new_length
                return start, old_length
            else:
                # Log does not exists, but the definition does -> return position at the end of the class
                last = next(reversed(index.values()))
                start = last[0] + last[1]
                index[guid] = start, new_length
                return start, 0

        else:
            # Flow definition for path must be created
            index = OrderedDict()
            self.__index_by_path[path] = index

            self.appendPlainText("class FlowDefinition{}:".format(re.sub('\W|^(?=\d)', '_', path)))
            self.appendPlainText("    url = host + '{}?wsdl".format(path))
            self.appendPlainText("    client = suds.client.Client(url)")
            self.appendPlainText("    flow = SoapFlow(client, '{}')".format(path))
            self.appendPlainText("\n")

            start = len(self.toPlainText())
            index[guid] = start, new_length
            return start, 0

    def __replace_text(self, start, old_length, snippet):
        text = self.toPlainText()
        length = len(snippet)
        old_end = start + old_length

        text = text[:start] + snippet + text[old_end:]
        self.setPlainText(text)

        length_diff = length - old_length
        if length_diff != 0:
            for index in self.__index_by_path.values():
                for guid, record in index.items():
                    if record[0] > old_end:
                        index[guid] = record[0] + length_diff, length
