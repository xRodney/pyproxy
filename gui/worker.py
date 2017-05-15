from PyQt5.QtCore import QObject, pyqtSignal, QSettings

from pipe import apipe
from pipe.communication import MessageListener, RequestResponse


class Worker(QObject, MessageListener):
    received = pyqtSignal(RequestResponse)
    error = pyqtSignal(Exception)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.thread = apipe.PipeThread(self)
        self.local_host = "localhost"
        self.local_port = None
        self.remote_port = None
        self.remote_host = None

    def start(self):
        if not self.thread.is_alive():
            self.thread.start()

        try:
            self.thread.start_proxy(self.local_host, int(self.local_port),
                                    self.remote_host, int(self.remote_port))
        except Exception as ex:
            self.on_error(ex)

    def stop(self):
        if self.thread.is_alive():
            self.thread.stop_proxy()

    def status(self):
        return self.thread.is_running()

    def on_request_response(self, request_response: RequestResponse):
        self.received.emit(request_response)

    def on_error(self, error):
        self.stop()
        self.error.emit(error)

    def save_state(self, settings: QSettings):
        settings.setValue("local_port", self.local_port)
        settings.setValue("remote_port", self.remote_port)
        settings.setValue("remote_host", self.remote_host)

    def restore_state(self, settings: QSettings):
        if settings.value("local_port", None):
            self.local_port = settings.value("local_port")
        if settings.value("remote_port", None):
            self.remote_port = settings.value("remote_port")
        if settings.value("remote_host", None):
            self.remote_host = settings.value("remote_host")
