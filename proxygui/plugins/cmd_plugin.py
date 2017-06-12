import shlex
import subprocess
from threading import Thread

from PyQt5.QtCore import QSettings
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QPlainTextEdit, QLineEdit, QPushButton, \
    QVBoxLayout, QHBoxLayout, QWidget

from proxygui.plugins.abstract_plugins import Plugin, SettingsPlugin, TabPlugin

DEFAULT_COMMAND = "while true; do echo \"" \
                  "Proxy run on: ${local_address}:${local_port} -> ${remote_address}:${remote_port}\"; " \
                  "sleep 1; done"


class CmdPlugin(Plugin, SettingsPlugin, TabPlugin):
    def __init__(self):
        super().__init__("Command plugin")
        self.widget = None
        self.worker = None

    def save_settings(self, settings):
        settings.beginGroup("cmd_plugin")
        settings.setValue("command", self.worker.command)
        settings.setValue("work_dir", self.worker.work_dir)
        settings.endGroup()

    def restore_settings(self, settings: QSettings):
        self.worker = CmdWorder()
        self.worker.onOutput.connect(self.__on_output)

        settings.beginGroup("cmd_plugin")
        if settings.value("command", None):
            self.worker.command = settings.value("command")
        if settings.value("work_dir", None):
            self.worker.work_dir = settings.value("work_dir")
        settings.endGroup()

    def get_tabs(self, data):
        yield lambda state: self.__build_tab(state), "Command runner"

    def __build_tab(self, state):
        if not self.widget:
            self.worker.parameters = self.plugin_registry.parameters
            self.widget = QWidget()
            vbox = QVBoxLayout()

            workDirEdit = QLineEdit()
            workDirEdit.setText(self.worker.work_dir)
            workDirEdit.textChanged.connect(self.__workDirChanged)
            vbox.addWidget(workDirEdit)

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

    def __workDirChanged(self, event):
        self.worker.work_dir = event

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

    def __init__(self):
        super().__init__()
        self.parameters = None
        self.thread = None
        self.command = DEFAULT_COMMAND
        self.work_dir = None

    def start(self):
        command = self.command
        command = command.replace("${local_address}", self.parameters.local_address)
        command = command.replace("${local_port}", str(self.parameters.local_port))
        command = command.replace("${remote_address}", self.parameters.remote_address)
        command = command.replace("${remote_port}", str(self.parameters.remote_port))
        self.thread = CmdThread(command, self.work_dir, self.__on_output)
        self.thread.start()

    def stop(self):
        self.thread.stop()
        self.thread = None

    def __on_output(self, outs, errs):
        self.onOutput.emit((outs, errs))

    def isRunning(self):
        return self.thread is not None


class CmdThread(Thread):
    def __init__(self, command, work_dir, listener):
        Thread.__init__(self, daemon=True)
        self.work_dir = work_dir if work_dir else None
        self.listener = listener
        self.command = command
        self.stop_requested = False

    def run(self):
        args = shlex.split(self.command)
        proc = subprocess.Popen(self.command, universal_newlines=True, shell=True, bufsize=0, cwd=self.work_dir,
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
