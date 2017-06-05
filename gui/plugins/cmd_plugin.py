import shlex
import subprocess
from threading import Thread

from PyQt5.QtCore import QSettings
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QPlainTextEdit, QLineEdit, QPushButton, \
    QVBoxLayout, QHBoxLayout, QWidget

from gui.plugins.abstract_plugins import Plugin, TabPlugin, \
    SettingsPlugin

DEFAULT_COMMAND = "while true; do echo \"" \
                  "Proxy run on: ${local_address}:${local_port} -> ${remote_address}:${remote_port}\"; " \
                  "sleep 1; done"


class CmdPlugin(Plugin, SettingsPlugin, TabPlugin):
    def __init__(self):
        super().__init__("Command plugin")
        self.widget = None
        self.worker = None

    def save_settings(self, settings):
        settings.setValue("command_plugin_command", self.command)

    def restore_settings(self, settings: QSettings):

        if settings.value("command_plugin_command", None):
            self.worker.command = settings.value("command_plugin_command")

    def get_tabs(self, data):
        yield lambda state: self.__build_tab(state), "Command runner"

    def __build_tab(self, state):
        if not self.widget:
            self.worker = CmdWorder(self.plugin_registry.parameters)
            self.worker.onOutput.connect(self.__on_output)

            self.widget = QWidget()
            vbox = QVBoxLayout()

            hbox = QHBoxLayout()
            cmdEdit = QLineEdit()
            cmdEdit.setText(self.worker.command)
            cmdEdit.textChanged.connect(self.__commandChanged)
            runBtn = QPushButton("Run / Stop")
            runBtn.clicked.connect(self.__btnClicked)

            hbox.addWidget(cmdEdit)
            hbox.addWidget(runBtn)
            vbox.addLayout(hbox)

            self.output = QPlainTextEdit()
            self.output.setReadOnly(True)
            self.output.setPlainText("Output")
            vbox.addWidget(self.output)

            self.widget.setLayout(vbox)

        return self.widget

    def __btnClicked(self, event):
        if not self.worker.isRunning():
            self.output.clear()
            self.worker.start()
        else:
            self.worker.stop()

    def __commandChanged(self, event):
        self.worker.command = event

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

    def __init__(self, parameters):
        super().__init__()
        self.parameters = parameters
        self.thread = None
        self.command = DEFAULT_COMMAND

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
