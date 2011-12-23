################################################################################
##                                                                            ##
## This file is a part of TADEK.                                              ##
##                                                                            ##
## TADEK - Test Automation in a Distributed Environment                       ##
## (http://tadek.comarch.com)                                                 ##
##                                                                            ##
## Copyright (C) 2011 Comarch S.A.                                            ##
## All rights reserved.                                                       ##
##                                                                            ##
## TADEK is free software for non-commercial purposes. For commercial ones    ##
## we offer a commercial license. Please check http://tadek.comarch.com for   ##
## details or write to tadek-licenses@comarch.com                             ##
##                                                                            ##
## You can redistribute it and/or modify it under the terms of the            ##
## GNU General Public License as published by the Free Software Foundation,   ##
## either version 3 of the License, or (at your option) any later version.    ##
##                                                                            ##
## TADEK is distributed in the hope that it will be useful,                   ##
## but WITHOUT ANY WARRANTY; without even the implied warranty of             ##
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the              ##
## GNU General Public License for more details.                               ##
##                                                                            ##
## You should have received a copy of the GNU General Public License          ##
## along with TADEK bundled with this file in the file LICENSE.               ##
## If not, see http://www.gnu.org/licenses/.                                  ##
##                                                                            ##
## Please notice that Contributor Agreement applies to any contribution       ##
## you make to TADEK. The Agreement must be completed, signed and sent        ##
## to Comarch before any contribution is made. You should have received       ##
## a copy of Contribution Agreement along with TADEK bundled with this file   ##
## in the file CONTRIBUTION_AGREEMENT.pdf or see http://tadek.comarch.com     ##
## or write to tadek-licenses@comarch.com                                     ##
##                                                                            ##
################################################################################

from PySide import QtCore
from PySide import QtGui

from tadek.core import settings

import utils

class _EscapeFilter(QtCore.QObject):
    '''
    An event filter that intercepts ESCAPE key press events
    '''
    initialText = None

    def eventFilter(self, obj, event):
        if (event.type() == QtCore.QEvent.KeyPress and
            event.key() == QtCore.Qt.Key_Escape):
            obj.setText(self.initialText)
            return True
        else:
            return QtCore.QObject.eventFilter(self, obj, event)


class SettingsDialog(QtCore.QObject):
    '''
    A manage settings dialog class.
    '''
    _SETTINGS_UI = "settings_dialog.ui"

    def __init__(self):
        QtCore.QObject.__init__(self)
        elements = utils.loadUi(self._SETTINGS_UI, parent=utils.window())
        self.columnEdited = 0
        self.dialog = elements["Dialog"]
        elements["buttonClose"].clicked.connect(self.dialog.close)
        self._optionsTree = elements["treeWidgetOptions"]
        self._optionsTree.setColumnWidth(2, 0)
        self._actionAdd = QtGui.QAction("&Add", self._optionsTree)
        self._actionRemove = QtGui.QAction("&Remove",
                                                          self._optionsTree)
        self._actionRefresh = QtGui.QAction("Re&fresh", self._optionsTree)
        self._menu = QtGui.QMenu("Menu", None)
        self._menu.addAction(self._actionAdd)
        self._menu.addAction(self._actionRemove)
        self._menu.addAction(self._actionRefresh)
        self._optionsTree.itemExpanded.connect(self.expandOption)
        self._optionsTree.itemDoubleClicked.connect(self.startEditing)
        self._optionsTree.currentItemChanged.connect(self.finishEditing)
        self._optionsTree.itemChanged.connect(self.updateOption)
        self._actionAdd.triggered.connect(self.addSetting)
        self._actionRemove.triggered.connect(self.removeSetting)
        self._actionRefresh.triggered.connect(self.reloadTree)
        self._optionsTree.customContextMenuRequested.connect(
                                                        self.contextMenuShow)
        self._escapeFilter = _EscapeFilter()

# Private methods:
    def _updateTree(self, parent=None, name=None, section=None):
        '''
        Fills the tree with settings options.
        '''
        if not parent:
            self._optionsTree.clear()
            for name in sorted(settings.get()):
                if settings.get(name) is not None:
                    settItem = QtGui.QTreeWidgetItem(self._optionsTree,
                                                     [name, "",])
                    settItem.customData = [name, None, None]
                    self._updateTree(settItem, name)
        elif parent and name and not section:
            for section in sorted(settings.get(name)):
                if settings.get(name, section) is not None:
                    sectionItem = QtGui.QTreeWidgetItem(parent, [section, "",])
                    sectionItem.customData = [name, section, None]
                    self._updateTree(sectionItem, name, section)
        elif parent and name and section:
            if settings.get(name, section) is not None:
                for option in sorted(settings.get(name, section),
                                     key=lambda s: s.name()):
                    optionItem = QtGui.QTreeWidgetItem(parent,
                                                [option.name(), str(option)])
                    optionItem.customData = [name, section, option.name()]

    def _expandItemRecursiveUp(self, item):
        '''
        Expands tree recursively using parent() function.
        '''
        item.setExpanded(True)
        itemParent = item.parent()
        if itemParent is not None:
            self._expandItemRecursiveUp(itemParent)

    def _reloadTree(self, cItem):
        '''
        Reload tree and reexpand item, which was selected.
        '''
        if cItem:
            path = cItem.text(0)
            cData = cItem.customData
            self._updateTree()
            items = self._optionsTree.findItems(path, QtCore.Qt.MatchRecursive,
                                                0)
            for item in items:
                if item.customData == cData:
                    self._expandItemRecursiveUp(item)
                    break
        else:
            self._updateTree()

# Slots:
    #@QtCore.Slot()
    def run(self):
        '''
        Displays the dialog.
        '''
        self._updateTree()
        self.dialog.show()

    #@QtCore.Slot(QtGui.QTreeWidgetItem)
    def expandOption(self, item):
        '''
        Aligns the first column of the tree.
        '''
        self._optionsTree.resizeColumnToContents(0)
        self._optionsTree.resizeColumnToContents(1)

    #@QtCore.Slot(QtGui.QTreeWidgetItem, int)
    def updateOption(self, item, column):
        '''
        Finishes editing an option item and saves changes to settings.
        '''
        if column == 0:
            self._optionsTree.closePersistentEditor(item, 0)
            data = item.customData[:]
            settings.get(*data).remove()
            data[-1] = item.text(0)
            settings.set(*data, value=item.text(1), force=True)
        elif column == 1:
            self._optionsTree.closePersistentEditor(item, 1)
            data = item.customData[:]
            data.append(item.text(1))
            settings.get(*data[:-1]).set(data[-1])

    #@QtCore.Slot(QtGui.QTreeWidgetItem, int)
    def startEditing(self, item, column):
        '''
        Begins editing an option item.
        '''
        if item.customData[2]:
            self._optionsTree.openPersistentEditor(item, column)
            # Filtering ESC key events as a workaround to PySide crash:
            # http://bugs.pyside.org/show_bug.cgi?id=800
            # http://bugreports.qt.nokia.com/browse/QTBUG-18848
            editor = self._optionsTree.findChild(QtGui.QLineEdit)
            if editor:
                editor.installEventFilter(self._escapeFilter)
                self._escapeFilter.initialText = editor.text()
            self.columnEdited = column

    #@QtCore.Slot(QtGui.QTreeWidgetItem, QtGui.QTreeWidgetItem)
    def finishEditing(self, current, previous):
        '''
        Finishes editing an option item.
        '''
        if (hasattr(previous, "customData") and 
            previous.customData[-1] is not None):
            self._optionsTree.closePersistentEditor(previous, self.columnEdited)

    #@QtCore.Slot()
    def addSetting(self):
        '''
        Adds new settings option or section.
        '''
        cData = self._optionsTree.currentItem().customData
        name, ok = QtGui.QInputDialog.getText(None, 'Enter name', 'Enter name')
        if ok and name != '':
            if cData[1] is None:
                settings.get(cData[0], name, force=True)
            else:
                value, ok = QtGui.QInputDialog.getText(None, 'Enter value',
                                                       'Enter value')
                if ok:
                    settings.get(cData[0], cData[1], name).set(value)
            self._reloadTree(self._optionsTree.currentItem())

    #@QtCore.Slot()
    def removeSetting(self):
        '''
        Remove settings option, section of file.
        '''
        rep = QtGui.QMessageBox.warning(None, "Are You sure ?",
        """Delete this settings ?\n
Settings will be deleted and they may be reverted to default
values when application will need this""",
                QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        if rep == QtGui.QMessageBox.Yes:
            cData = self._optionsTree.currentItem().customData
            option = settings.get(cData[0], cData[1], cData[2])
            option.remove()
            self._reloadTree(self._optionsTree.currentItem().parent())

    #@QtCore.Slot()
    def reloadTree(self):
        '''
        Reloads the tree widget.
        '''
        self._reloadTree(self._optionsTree.currentItem())

    #@QtCore.Slot(QtCore.QPoint)
    def contextMenuShow(self, point):
        '''
        Overrides context menu handler.
        '''
        if self._optionsTree.currentItem():
            # Top level items:
            if self._optionsTree.currentItem().customData[1:] == [None, None]:
                self._actionAdd.setEnabled(True)
                self._actionRemove.setEnabled(False)
            # Section items:
            elif self._optionsTree.currentItem().customData[-1] is None:
                self._actionAdd.setEnabled(True)
                self._actionRemove.setEnabled(True)
            else:
                self._actionAdd.setEnabled(False)
                self._actionRemove.setEnabled(True)
        else:
            self._actionRemove.setEnabled(False)
            self._actionAdd.setEnabled(False)
        self._menu.exec_(self._optionsTree.viewport().mapToGlobal(point))

