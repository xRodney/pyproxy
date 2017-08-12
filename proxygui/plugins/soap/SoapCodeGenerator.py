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
        self.__index_by_guid = OrderedDict()
        self.__index_by_url = OrderedDict()

    def refresh(self):
        pass

    def onLogChange(self, log, is_new, all_messages):
        is_new = log.guid not in self.__index_by_guid

        if self.soap_plugin.is_soap(log.response):
            snippet = self.soap_plugin.soap_code(log.response, log, level=1) + "\n"

            if is_new:
                start = self.__get_start_for_url(log.request)
                old_length = 0
            else:
                start, old_length = self.__index_by_guid[log.guid]

            self.__index_by_guid[log.guid] = (start, len(snippet))
            self.__replace_text(start, old_length, snippet)

    def __get_start_for_url(self, request):
        return len(self.toPlainText())

    def __replace_text(self, start, old_length, snippet):
        text = self.toPlainText()
        length = len(snippet)

        text = text[:start] + snippet + text[start + old_length:]
        self.setPlainText(text)

        length_diff = length - old_length
        if length_diff != 0:
            for index in self.__index_by_guid.values():
                if index[0] > start:
                    index[0] += length_diff
