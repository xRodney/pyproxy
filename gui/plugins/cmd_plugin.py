import shlex
import subprocess
from PyQt5 import QtGui
from collections import OrderedDict
from threading import Thread

from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont, QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QPlainTextEdit, QDialog, QFormLayout, QLabel, QLineEdit, QCheckBox, QPushButton, \
    QVBoxLayout, QHBoxLayout, QTreeView, QWidget

from gui.plugins.abstract_plugins import Plugin, GridPlugin, ContentViewPlugin, SettingsMenuPlugin, TabPlugin, \
    SettingsPlugin
from parser.http_parser import HttpMessage, HttpRequest
from pipe.communication import RequestResponse
from utils import soap2python


class CmdPlugin(Plugin, SettingsPlugin, TabPlugin):
    def __init__(self):
        super().__init__("Command plugin")
        self.command = "while true; do echo \"Proxy run on: ${local_address}:${local_port} -> ${remote_address}:${remote_port}\"; sleep 1; done"

    def save_settings(self, settings):
        settings.setValue("command_plugin_command", self.command)

    def restore_settings(self, settings: QSettings):
        if settings.value("command_plugin_command", None):
            self.command = settings.value("command_plugin_command")

    def get_tabs(self, data):
        yield lambda state: self.__build_tab(state), "Command runner"

    def __build_tab(self, state):
        widget = QWidget()
        vbox = QVBoxLayout()

        hbox = QHBoxLayout()
        cmdEdit = QLineEdit()
        cmdEdit.setText(self.command)
        runBtn = QPushButton("Run / Stop")
        runBtn.clicked.connect(self.__btnClicked)

        hbox.addWidget(cmdEdit)
        hbox.addWidget(runBtn)
        vbox.addLayout(hbox)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlainText("Output")
        vbox.addWidget(self.output)

        widget.setLayout(vbox)

        self.worker = CmdWorder(self.command, self.plugin_registry.parameters)
        self.worker.onOutput.connect(self.__on_output)

        return widget

    def __btnClicked(self, event):
        if not self.worker.isRunning():
            self.output.clear()
            self.worker.start()
        else:
            self.worker.stop()

    def __on_output(self, outs_errs):
        outs, errs = outs_errs

        sb = self.output.verticalScrollBar()
        at_max = sb.value() == sb.maximum()

        if outs:
            self.output.appendPlainText(outs)
        if errs:
            self.output.appendPlainText(errs)

        if at_max:
            sb.setValue(sb.maximum())


class CmdWorder(QWidget):
    onOutput = pyqtSignal(tuple)

    def __init__(self, command, parameters):
        super().__init__()
        self.parameters = parameters
        self.thread = None
        self.command = command

    def start(self):
        command = self.command
        command = command.replace("${local_address}", self.parameters.local_address)
        command = command.replace("${local_port}", str(self.parameters.local_port))
        command = command.replace("${remote_address}", self.parameters.remote_address)
        command = command.replace("${remote_port}", str(self.parameters.remote_port))
        self.thread = CmdThread(command, self.__on_output)
        self.thread.start()

    def stop(self):
        self.thread.stop()
        self.thread = None

    def __on_output(self, outs, errs):
        self.onOutput.emit((outs, errs))

    def isRunning(self):
        return self.thread is not None


class CmdThread(Thread):
    def __init__(self, command, listener):
        Thread.__init__(self, daemon=True)
        self.listener = listener
        self.command = command
        self.stop_requested = False

    def run(self):
        args = shlex.split(self.command)
        proc = subprocess.Popen(self.command, universal_newlines=True, shell=True, bufsize=0,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        line = proc.stdout.readline()
        while line and not self.stop_requested:
            self.listener(line, None)
            line = proc.stdout.readline()

        proc.kill()
        outs, errs = proc.communicate()
        self.listener(outs, errs)

    def stop(self):
        self.stop_requested = True
