import signal
import sys

from PyQt5.QtWidgets import (QApplication)

from proxygui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)

    # Allow the app to be killed by Ctrl+C (otherwise the Qt window would stay open)
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    ex = MainWindow()
    if len(sys.argv) == 2:
        ex.load(sys.argv[1])
    sys.exit(app.exec_())
