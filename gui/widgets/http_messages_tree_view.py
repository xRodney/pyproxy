from collections import OrderedDict

from PyQt5.QtCore import pyqtSignal, QItemSelection
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QTreeView

from pipe.communication import RequestResponse

ROLE_HTTP_MESSAGE = 45454


class HttpMessagesTreeView(QTreeView):
    selected = pyqtSignal(object)

    class ModelItem:
        def __init__(self, model, branch):
            self.branch = branch
            self.model = model

    def __init__(self, plugins, parent=None):
        super().__init__(parent)
        self.plugins = plugins
        self.clear()
        self.selectionModel().selectionChanged.connect(self.onSelectionChanged)

    def getBranch(self, rr: RequestResponse):
        if rr.guid in self.__index:
            model_item = self.__index[rr.guid]
            branch = model_item.branch
            model_item.model = rr
        else:
            branch = [QStandardItem(), QStandardItem(), QStandardItem()]
            self.rootNode.appendRow(branch)
            self.__index[rr.guid] = HttpMessagesTreeView.ModelItem(rr, branch)

        return branch

    def getAllMessagePairs(self):
        return (item.model for item in self.__index.values())

    def clear(self):
        self.model = QStandardItemModel()
        self.rootNode = self.model.invisibleRootItem()
        self.__index = OrderedDict()
        self.setModel(self.model)

    def applyModel(self):
        self.setModel(self.model)
        column_count = self.model.columnCount()
        column_width = self.width() / column_count
        for col in range(0, column_count):
            self.setColumnWidth(col, column_width)

    def onSelectionChanged(self, selection: QItemSelection):
        if selection.isEmpty():
            return
        item = selection.indexes()[0]
        data = item.data(ROLE_HTTP_MESSAGE)
        if data:
            self.selected.emit(data)
