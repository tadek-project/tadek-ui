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

from tadek.engine.testexec import (STATUS_PASSED, STATUS_FAILED, STATUS_ERROR,
                                   STATUS_NOT_COMPLETED)
from tadek.engine.channels.summarychannel import (COUNTER_N_TESTS,
                        COUNTER_TESTS_RUN, COUNTER_RUN_TIME, COUNTER_CORE_DUMPS)

from utils import loadUi, window, STATUS_COLORS

class LoadingErrorDialog(QtCore.QObject):
    '''
    A dialog class for displaying information about errors that occurred while
    importing modules.
    '''
    _DIALOG_UI = "test/loaderror_dialog.ui"
    
    def __init__(self, header, errors):
        '''
        Sets title of the dialog and fills the tree with information stored
        in given list of ErrorBox instances.
        '''
        QtCore.QObject.__init__(self)
        elements = loadUi(self._DIALOG_UI, parent=window())
        self._dialog = elements["dialog"]
        self._dialog.setWindowTitle(header)
        tree = elements["treeWidgetErrors"]
        items = []
        for error in errors:
            item = QtGui.QTreeWidgetItem(tree)
            infos = []
            fields = vars(error)
            for name in sorted(fields):
                if name != "traceback":
                    infos.append(fields[name])
            item.setText(0, ", ".join(infos))
            QtGui.QTreeWidgetItem(item, [error.traceback])
            item.setExpanded(True)
            items.append(item)
        tree.resizeColumnToContents(0)
        size = QtCore.QSize(min(window().size().width(),
                                tree.columnWidth(0) + 40),
                            min(window().size().height(),
                                self._dialog.size().height()))
        self._dialog.resize(size)
        for item in items:
            item.setExpanded(False)

    def run(self):
        '''
        Shows the dialog.
        '''
        self._dialog.show()


class ReportDialog(QtCore.QObject):
    '''
    A dialog class for displaying test cases execution reports.
    '''
    _DIALOG_UI = "test/report_dialog.ui"

    _names = {
        COUNTER_N_TESTS:      "Total Tests",
        COUNTER_TESTS_RUN:    "Tests Started",
        STATUS_PASSED:        "Tests Passed",
        STATUS_FAILED:        "Tests Failed",
        STATUS_ERROR:         "Tests with Error",
        STATUS_NOT_COMPLETED: "Tests Not Completed",
        COUNTER_CORE_DUMPS:   "Core Dumps",
        COUNTER_RUN_TIME:     "Execution Time"
    }

    _icons = {
        STATUS_PASSED:        QtGui.QIcon(":/test/icons/dialog-ok-apply.png"),
        STATUS_FAILED:        QtGui.QIcon(":/test/icons/edit-delete.png"),
        STATUS_ERROR:         QtGui.QIcon(":/test/icons/emblem-important.png"),
        STATUS_NOT_COMPLETED: QtGui.QIcon(":/test/icons/user-away-extended.png"
                                          ),
        COUNTER_CORE_DUMPS:   QtGui.QIcon(":/test/icons/edit-bomb.png"),
    }
    
    _colors = {
        COUNTER_CORE_DUMPS:   QtGui.QBrush(QtCore.Qt.darkYellow),
    }
    _colors.update(STATUS_COLORS)

    closed = QtCore.Signal()
    runAgainClicked = QtCore.Signal()
    showDetailsClicked = QtCore.Signal()

    def __init__(self, summary, files, runAgain=True):
        '''
        Takes a dictionary with summary of a test execution and a dictionary
        of files produced by channels and builds a tree. If runAgain is True,
        then the 'Run Again' button will be enabled.
        '''
        QtCore.QObject.__init__(self)
        elements = loadUi(self._DIALOG_UI, parent=window())
        self._dialog = elements["dialog"]
        self._tree = elements["treeWidgetReport"]
        raButton = elements["buttonRunAgain"]
        sdButton = elements["buttonShowDetails"]
        elements["buttonClose"].clicked.connect(self._dialog.accept)
        self._dialog.finished.connect(self.closed)
        if runAgain is False:
            raButton.setEnabled(False)
        else:
            raButton.clicked.connect(self._dialog.accept)
            raButton.clicked.connect(self.runAgainClicked)
        sdButton.clicked.connect(self._dialog.accept)
        sdButton.clicked.connect(self.showDetailsClicked)
        sdButton.setDefault(True)
        font = self._tree.font()
        font.setPointSize(font.pointSize() + 2)
        self._largeFont = font
        font = QtGui.QFont(font)
        font.setBold(True)
        self._largeBoldFont = font
        self._metrics = QtGui.QFontMetrics(self._largeBoldFont)
        self._tree.header().setResizeMode(
            QtGui.QHeaderView.ResizeMode.ResizeToContents)
        self._tree.header().sectionResized.connect(self._update,
                                                   QtCore.Qt.QueuedConnection)

        useColor = {
            STATUS_PASSED: (summary[STATUS_PASSED] > 0 and
                            (summary[STATUS_FAILED] +
                             summary[STATUS_NOT_COMPLETED] +
                             summary[STATUS_NOT_COMPLETED]) == 0),
            STATUS_FAILED: summary[STATUS_FAILED] > 0, 
            STATUS_ERROR: summary[STATUS_ERROR] > 0,
            STATUS_NOT_COMPLETED: summary[STATUS_NOT_COMPLETED] > 0,
            COUNTER_CORE_DUMPS: summary[COUNTER_CORE_DUMPS] > 0
        }
        
        for id in (COUNTER_N_TESTS, COUNTER_TESTS_RUN, STATUS_PASSED,
                   STATUS_FAILED, STATUS_NOT_COMPLETED, STATUS_ERROR,
                   COUNTER_CORE_DUMPS, COUNTER_RUN_TIME):
            if id == COUNTER_CORE_DUMPS and summary[COUNTER_CORE_DUMPS] == 0:
                continue 
            self._addItem(id, str(summary[id]), useColor.get(id, False))

        self._filesItems = []
        for name, value in files:
            self._addItem(name, value, False, file=True)

        header = self._tree.header()
        for i in xrange(3):
            header.setResizeMode(i, header.ResizeToContents)

    def _addItem(self, id, value, color, file=False):
        '''
        Adds an item to the tree.
        '''
        item = QtGui.QTreeWidgetItem(self._tree,
                                     ["", self._names.get(id, id), value])
        if id in self._icons:
            item.setIcon(0, self._icons[id])
        if color:
            c = self._colors.get(id, QtCore.Qt.black)
            item.setForeground(1, c)
            item.setForeground(2, c)
        item.setFont(1, self._largeFont)
        item.setFont(2, self._largeBoldFont)
        if file:
            item.setTextAlignment(1, QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
            self._filesItems.append((item, value))
        else:
            item.setTextAlignment(2, QtCore.Qt.AlignRight)

    def _update(self, index, size, oldSize):
        '''
        Rebuilds the tree in such way that texts of all items with file paths
        are visible.
        '''
        if index != 2:
            return
        self._tree.setUpdatesEnabled(False)
        for item, value in self._filesItems:
            parts = []
            l = len(value)
            s = self._tree.header().sectionSize(2)
            for i in xrange(1, l + 1):
                m = i
                del parts[:]
                mod =  l % m
                for i in xrange(l / m):
                    parts.append(value[i * m:(i + 1) * m])
                if mod:
                    parts.append(value[-mod:])
                fit = True
                for p in parts:
                    if self._metrics.width(p) + 20 > s:
                        fit = False
                        break
                if not fit:
                    break
            item.setText(2, "\n".join(parts))
            if len(parts) > 1:
                item.setTextAlignment(2, QtCore.Qt.AlignLeft)
            else:
                item.setTextAlignment(2, QtCore.Qt.AlignRight)
        self._tree.setUpdatesEnabled(True)

    def run(self):
        '''
        Shows the dialog and waits until it is closed.
        '''
        self._dialog.exec_()

