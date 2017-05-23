from collections import OrderedDict

from PyQt5.QtCore import pyqtSignal, QItemSelection, Qt, QSortFilterProxyModel
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QTreeView

ROLE_HTTP_MESSAGE = 45454


class FilteredModel(QSortFilterProxyModel):
    def __init__(self, plugin_registry):
        super().__init__()
        self.plugin_registry = plugin_registry

    def filterAcceptsRow(self, source_row, source_parent):
        index = self.sourceModel().index(source_row, 0, source_parent)
        data = self.sourceModel().data(index, ROLE_HTTP_MESSAGE)
        return self.plugin_registry.filter_accepts_row(data)


class HttpMessagesTreeView(QTreeView):
    selected = pyqtSignal(object)

    class ModelItem:
        def __init__(self, model, branch):
            self.branch = branch
            self.model = model

    def __init__(self, plugin_registry, parent=None):
        super().__init__(parent)
        self.plugin_registry = plugin_registry
        self.clear()
        self.selectionModel().selectionChanged.connect(self.onSelectionChanged)
        self.column_definitions = self.plugin_registry.get_columns()

    def getAllMessagePairs(self):
        return (item.model for item in self.__index.values())

    def clear(self):
        self.model = QStandardItemModel()
        self.filteredModel = FilteredModel(self.plugin_registry)
        self.filteredModel.setSourceModel(self.model)

        self.rootNode = self.model.invisibleRootItem()
        self.__index = OrderedDict()
        self.setModel(self.filteredModel)

    def refresh(self):
        self.filteredModel.invalidateFilter()

    def applyModel(self):
        self.setModel(self.filteredModel)
        for i, column in enumerate(self.column_definitions):
            self.model.setHeaderData(i, Qt.Horizontal, column[1]);
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

    def onRequestResponse(self, request_response):
        new_row = request_response.guid not in self.__index

        if not new_row:
            model_item = self.__index[request_response.guid]
            branch = model_item.branch
            model_item.model = request_response
        else:
            branch = [QStandardItem() for x in self.column_definitions]
            self.__index[request_response.guid] = HttpMessagesTreeView.ModelItem(request_response, branch)

        branch[0].setData(request_response, ROLE_HTTP_MESSAGE)

        for i, column in enumerate(self.column_definitions):
            text = self.plugin_registry.get_cell_content(request_response, column[0])
            if text:
                branch[i].setText(text)

        if new_row:
            self.rootNode.appendRow(branch)
        self.applyModel()
