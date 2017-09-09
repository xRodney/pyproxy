from PyQt5.QtCore import QObject, pyqtSignal

from proxycore.pipe import apipe
from proxycore.pipe.apipe import ProxyParameters
from proxycore.pipe.reporting import MessageListener, LogReport


class Worker(QObject, MessageListener):
    received = pyqtSignal(LogReport)
    error = pyqtSignal(Exception)
    running_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.thread = apipe.PipeThread(self)
        self.parameters = None

    def start(self):
        if not self.thread.is_alive():
            self.thread.start()

        try:
            self.thread.start_proxy(self.parameters)
        except Exception as ex:
            self.on_error(ex)

        self.running_changed.emit(self.thread.is_running())

    def stop(self):
        if self.thread.is_alive():
            self.thread.stop_proxy()
        self.running_changed.emit(self.thread.is_running())

    def status(self):
        return self.thread.is_running()

    def on_change(self, log):
        self.received.emit(log)

    def on_error(self, error):
        self.stop()
        self.error.emit(error)

    def setParameters(self, parameters: ProxyParameters):
        self.parameters = parameters
