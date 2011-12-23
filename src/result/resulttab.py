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

from tadek.core import log
from tadek.core import settings
from tadek.engine.testexec import STATUS_PASSED, STATUS_FAILED, STATUS_ERROR
from tadek.engine.testresult import (TestStepResult, TestCaseResult,
                                     TestSuiteResult)

from utils import viewName, STATUS_COLORS, STATUS_FONTS


class ResultItem(QtGui.QTreeWidgetItem):
    '''
    Class of result tree items.
    '''

    def __init__(self, *args, **kwargs):
        self.testResult = kwargs.pop("testResult", None)
        self.testName = kwargs.pop("testName", None) 
        QtGui.QTreeWidgetItem.__init__(self, *args, **kwargs)


class ResultTab(QtCore.QObject):
    '''
    Represents tab containing test results.
    '''
    _RESULT_TAB_UI = "result_tab.ui"
    _COLUMN_COUNT = 3

    _ICONS = {
        "directory": QtGui.QIcon(":/result/icons/folder-grey.png"),
        "module":    QtGui.QIcon(":/result/icons/text-x-python.png"),
        "suite":     QtGui.QIcon(":/result/icons/source_moc.png"),
        "case":      QtGui.QIcon(":/result/icons/inode-blockdevice.png"),
        "step":      QtGui.QIcon(":/result/icons/application-x-zip.png")
    }

    _expandStatuses = settings.get(viewName(), "options", "expand_statuses",
                                   default=",".join((STATUS_ERROR,
                                                     STATUS_FAILED)),
                                   force=True)

    def __init__(self, view, result, select, closable):
        '''
        Initializes tab with test results. The parameters are:
        - view: instance of ResultView
        - result: a test result instance
        - select: a boolean that determines whether tree items should be
            selected on adding
        - closable: a boolean that determines if tab can be closed manually
        '''
        QtCore.QObject.__init__(self)
        self._view = view
        elements = view.loadUi(self._RESULT_TAB_UI)
        self.tab = elements["Tab"]
        self._treeWidget = elements["treeWidget"]
        self._treeWidget.currentItemChanged.connect(self.display)
        self._treeWidget.itemExpanded.connect(self._updateOnExpand)
        self._treeWidget.itemCollapsed.connect(self._updateOnCollapse)
        self._closable = closable

        for res in result:
            log.debug("Adding tree item(s) for result '%s'" % res.id)
            self._addItem(res, None, select)
            for i in xrange(self._COLUMN_COUNT):
                self._treeWidget.resizeColumnToContents(i)

# Private methods:
    def _getItem(self, id, force=False):
        '''
        Returns an item related to a test result of given ID. If force is set
        to True, then an item will be created if it does not exist yet.
        '''
        sections = id.split(".")
        matchedItem = None
        parent = self._treeWidget
        for i in xrange(len(sections)):
            matchedItem = None
            if i == 0:
                for j in xrange(parent.topLevelItemCount()):
                    item = parent.topLevelItem(j)
                    if item.testName == sections[0]:
                        matchedItem = item
                        break
            else:
                for j in xrange(parent.childCount()):
                    item = parent.child(j)
                    if item.testName == ".".join(sections[:i+1]):
                        matchedItem = item
                        break
            if matchedItem is None:
                if not force:
                    return None
                item = ResultItem(parent, testName=".".join(sections[:i+1]))
                item.setText(0, sections[i])
                item.setIcon(0, self._ICONS["directory"])
                parent = item                    
            else:
                parent = matchedItem

        return parent

    def _addItem(self, result, parent, select):
        '''
        Adds items to the tree based on given result and its descendants.
        The select boolean determines whether items should be selected.
        '''
        item = None
        if parent is None:
            item = self._getItem(result.id)
            if item is None:
                parent = self._getItem(".".join(result.id.split(".")[:-1]),
                                       force=True)
        if item is None:
            item = ResultItem(parent, testName=result.id, testResult=result)
            if isinstance(result, TestSuiteResult):
                item.setIcon(0, self._ICONS["suite"])
                if item.parent().testResult is None:
                    item.parent().setIcon(0, self._ICONS["module"])
            elif isinstance(result, TestCaseResult):
                item.setIcon(0, self._ICONS["case"])
            elif isinstance(result, TestStepResult):
                item.setIcon(0, self._ICONS["step"])
            item.setText(1, result.id.rsplit(".", 1)[1])
            self._setItemStatus(item)
        if select:
            self._treeWidget.setCurrentItem(item)
        for childResult in result.children:
            self._addItem(childResult, item, select)

    def _setItemStatus(self, item):
        '''
        Sets color of a tree item adequately to status of its result and fills
        the 'Pass rate' column
        '''
        color = STATUS_COLORS[item.testResult.status]
        item.setForeground(1, color)
        item.setForeground(2, color)
        item.setFont(1, STATUS_FONTS[item.testResult.status])
        if isinstance(item.testResult, (TestCaseResult, TestSuiteResult)):
            i = p = 0
            for c in item.testResult.children:
                i += 1
                if c.status == STATUS_PASSED:
                    p += 1
            item.setText(2, "%d of %d" % (p, i))
        item.setTextAlignment(2, QtCore.Qt.AlignHCenter)

# Public methods:
    def isClosable(self):
        '''
        Returns True if tab can be closed or False otherwise.
        '''
        return self._closable

    def setClosable(self, closable):
        '''
        Sets the closable boolean attribute of the tab.
        '''
        self._closable = closable

    def update(self, result):
        '''
        Selects and updates status of a tree item corresponding to given result.
        '''
        log.debug("Selecting tree item for result '%s'" % result.id)
        item = self._getItem(result.id)
        self._setItemStatus(item)
        self._treeWidget.setCurrentItem(item)

    def refresh(self):
        '''
        Refreshes details of a test result that corresponds to the currently
        selected item.
        '''
        log.debug("Refreshing currently selected result item")
        item = self._treeWidget.currentItem()
        self._treeWidget.setCurrentItem(None)
        self._treeWidget.setCurrentItem(item)

    def expandItems(self):
        '''
        Expands tree items with statuses read from the settings option.
        '''
        items = self._treeWidget.findItems("*", QtCore.Qt.MatchRecursive |
                                           QtCore.Qt.MatchWildcard)
        for item in items:
            item.setExpanded(False)
        self._treeWidget.setCurrentItem(None)
        QtGui.qApp.processEvents()
        statuses = map(lambda s: s.strip(), self._expandStatuses.getList())
        log.debug("Expanding items of results: %s" % ",".join(statuses))
        for item in items:
            if (item.testResult and
                not isinstance(item.testResult, TestStepResult) and
                item.testResult.status in statuses):
                item.setExpanded(True)
                parent = item.parent()
                while parent:
                    parent.setExpanded(True)
                    parent = parent.parent()

# Slots:
    #@QtCore.Slot(QtGui.QTreeWidgetItem)
    def display(self, item):
        '''
        Displays details of given tree item.
        '''
        if self._view.isTabCurrent(self):
            if item is None or item.testResult is None:
                self._view.clearDetails()
            else:
                self._view.showDetails(item.testResult)

    #@QtCore.Slot()
    def expand(self):
        '''
        Expands the currently selected tree item.
        '''
        def expandRecursively(item):
            self._treeWidget.expandItem(item)
            for index in xrange(item.childCount()):
                expandRecursively(item.child(index))

        if self._view.isTabCurrent(self):
            log.debug("Expanding selected tree item")
            item = self._treeWidget.currentItem()
            if item:
                expandRecursively(item)

    #@QtCore.Slot()
    def expandAll(self):
        '''
        Expands all items in the tree.
        '''
        if self._view.isTabCurrent(self):
            log.debug("Expanding all tree items")
            self._treeWidget.expandAll()
            for i in xrange(self._COLUMN_COUNT):
                self._treeWidget.resizeColumnToContents(i)

    #@QtCore.Slot()
    def collapse(self):
        '''
        Collapses currently selected tree item.
        '''
        if self._view.isTabCurrent(self):
            log.debug("Collapsing selected tree item")
            self._treeWidget.collapseItem(self._treeWidget.currentItem())

    #@QtCore.Slot()
    def collapseAll(self):
        '''
        Collapses all items of tree.
        '''
        if self._view.isTabCurrent(self):
            log.debug("Collapsing all tree items")
            self._treeWidget.collapseAll()
            for i in xrange(self._COLUMN_COUNT):
                self._treeWidget.resizeColumnToContents(i)

    #@QtCore.Slot(QtGui.QTreeWidgetItem)
    def _updateOnExpand(self, item):
        '''
        Updates widths of columns in the tree to fit given tree item.
        '''
        if self._view.isTabCurrent(self):
            for i in xrange(self._COLUMN_COUNT):
                self._treeWidget.resizeColumnToContents(i)

    #@QtCore.Slot(QtGui.QTreeWidgetItem)
    def _updateOnCollapse(self, item):
        '''
        Clears result details in the Result view, sets the given item as
        current and updates widths of columns to fit it.
        '''
        if self._view.isTabCurrent(self):
            items = self._treeWidget.selectedItems()
            if items and items[0] is not item and items[0].parent():
                parent = items[0].parent()
                while True:
                    if parent is item:
                        self._view.clearDetails()
                        self._treeWidget.setCurrentItem(None)
                        break
                    if parent is None:
                        break
                    parent = parent.parent()
            for i in xrange(self._COLUMN_COUNT):
                self._treeWidget.resizeColumnToContents(i)

