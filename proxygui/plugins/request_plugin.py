import traceback
import urllib.request

from PyQt5.QtWidgets import QMessageBox

from proxygui.plugins.abstract_plugins import SettingsMenuPlugin, Plugin


class RequestPlugin(Plugin, SettingsMenuPlugin):
    def __init__(self):
        super().__init__("Test request plugin")

    def add_settings_menu(self):
        yield "Fire a test request", self.on_request_clicked

    def on_request_clicked(self):
        try:
            parameters = self.plugin_registry.parameters
            urllib.request.urlopen("http://{}:{}".format(parameters.local_address, parameters.local_port))
        except Exception as e:
            print(traceback.format_exc())
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("The request resulted in an error:")
            msg.setInformativeText(str(e))
            msg.setWindowTitle("Error")
            msg.exec_()
