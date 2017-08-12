from collections import OrderedDict

from PyQt5.QtCore import pyqtSignal, QItemSelection, Qt, QSortFilterProxyModel
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QTreeView, QWidget, QVBoxLayout, QLabel

ROLE_HTTP_MESSAGE = 45454


class FilteredModel(QSortFilterProxyModel):
    def __init__(self, plugin_registry):
        super().__init__()
        self.plugin_registry = plugin_registry

    def filterAcceptsRow(self, source_row, source_parent):
        index = self.sourceModel().index(source_row, 0, source_parent)
        data = self.sourceModel().data(index, ROLE_HTTP_MESSAGE)
        return self.plugin_registry.filter_accepts_row(data)


class HttpMessagesTreeView(QWidget):
    selected = pyqtSignal(object)

    class ModelItem:
        def __init__(self, model, branch):
            self.branch = branch
            self.model = model

    def __init__(self, plugin_registry, parent=None):
        super().__init__(parent)
        self.plugin_registry = plugin_registry
        self.tree_view = QTreeView()
        self.label = QLabel()
        self.clear()

        self.column_definitions = self.plugin_registry.get_columns()

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.tree_view)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def clear(self):
        self.model = QStandardItemModel()
        self.filteredModel = FilteredModel(self.plugin_registry)
        self.filteredModel.setSourceModel(self.model)

        self.rootNode = self.model.invisibleRootItem()
        self.__index = OrderedDict()
        self.tree_view.setModel(self.filteredModel)
        self.label.setText(self.__getLabelText())

        self.tree_view.selectionModel().selectionChanged.connect(self.onSelectionChanged)

    def refresh(self):
        self.filteredModel.invalidateFilter()
        self.label.setText(self.__getLabelText())

    def applyModel(self):
        self.tree_view.setModel(self.filteredModel)
        for i, column in enumerate(self.column_definitions):
            self.model.setHeaderData(i, Qt.Horizontal, column[1]);
        column_count = self.model.columnCount()
        column_width = self.tree_view.width() / column_count
        for col in range(0, column_count):
            self.tree_view.setColumnWidth(col, column_width)
        self.label.setText(self.__getLabelText())

    def onSelectionChanged(self, selection: QItemSelection):
        if selection.isEmpty():
            return
        item = selection.indexes()[0]
        data = item.data(ROLE_HTTP_MESSAGE)
        if data:
            self.selected.emit(data)

    def onLogChange(self, log, is_new, all_messages):

        if not is_new:
            model_item = self.__index[log.guid]
            branch = model_item.branch
            model_item.model = log
        else:
            branch = [QStandardItem() for x in self.column_definitions]
            self.__index[log.guid] = HttpMessagesTreeView.ModelItem(log, branch)

        branch[0].setData(log, ROLE_HTTP_MESSAGE)

        for i, column in enumerate(self.column_definitions):
            text = self.plugin_registry.get_cell_content(log, column[0])
            if text:
                branch[i].setText(text)

        if is_new:
            self.rootNode.appendRow(branch)
        self.applyModel()

    def __getLabelText(self):
        return "Displaying <b>{}</b> out of <b>{}</b>.".format(self.filteredModel.rowCount(),
                                                               self.model.rowCount())
