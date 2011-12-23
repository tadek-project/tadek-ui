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

import os

from PySide import QtCore
from PySide import QtGui

from tadek.core import log
from tadek.core import config
from tadek.core import utils
from tadek.engine.testresult import TestStepResult
from tadek.engine import channels

import icons
import dialogs
from view import View
from resulttab import ResultTab
from consolechannel import ConsoleChannelHelper, ConsoleChannel
from resultchannel import ResultChannelHelper, ResultChannel
from utils import (viewName, STATUS_COLORS, STATUS_FONTS, LastValues,
                   ClosableTabBar)

class Result(View):
    '''
    A view for analyzing test case results.
    '''
    NAME = viewName()
    _UI_FILE = "result_view.ui"
    _ICON_FILE = ":/result/icons/mail-mark-task.png"

    _CONFIG_SECTION_MENU = "menu"
    _CONFIG_SECTION_CONSOLE = "console"

    # Menus and Tool bar
    _menuFile = (
        "actionOpen",
        (
            "Recent &Files",
            "actionClearMenu"
        ),
        None,
        "actionClose"
    )
    _menuEdit = (
        "actionExpand",
        "actionExpandAll",
        "actionCollapse",
        "actionCollapseAll",
        None
    )
    _toolBar = (
        "actionOpen",
        "actionClose",
        None,
        (
            "actionExpand",
            "actionExpandAll",
        ),
        (
            "actionCollapse",
            "actionCollapseAll"
        )
    )

    def __init__(self, *args):
        View.__init__(self, *args)

        # Recent files menu
        self._recentFiles = LastValues(self.NAME, self._CONFIG_SECTION_MENU,
                                       "recent", 5)
        self._actionClearMenu = self._elements["actionClearMenu"]
        self._menuRecentFiles = self._menuFile[1]
        self._actionClearMenu.triggered.connect(self._recentFiles.clear)
        self._actionClearMenu.triggered.connect(self._updateRecentFiles)

        # Widgets
        self._treeWidget = self._elements["treeWidgetInfo"]
        self._tabWidget = self._elements["tabWidgetResults"]
        self._tabWidget.setTabBar(ClosableTabBar())
        self._widgetConsole = self._elements["widgetConsole"]
        self._buttonShowConsole = self._elements["buttonShowConsole"]
        self._buttonHideConsole = self._elements["buttonHideConsole"]
        self._splitterConsole = self._elements["splitterConsole"]
        self._buttonSaveOutput = self._elements["buttonSaveOutput"]
        self._textEdit = self._elements["textEditConsole"]
        self._tabs = {}
        self._treeWidget.setColumnCount(2)
        self._treeWidget.header().resizeSection(2, 0)
        self._treeWidget.header().setHorizontalScrollMode(
            QtGui.QAbstractItemView.ScrollPerPixel)
        self._treeWidget.header().setResizeMode(1,
            QtGui.QHeaderView.ResizeToContents)
        self._treeWidget.header().setResizeMode(2, QtGui.QHeaderView.Fixed)
        self._treeWidget.header().setStretchLastSection(True)
        self._widgetConsole.setVisible(False)
        self._buttonHideConsole.setVisible(False)
        self._tabWidget.currentChanged[int].connect(self._displaySelected)
        self._tabWidget.tabCloseRequested.connect(self._closeTabOfIndex)
        self._buttonShowConsole.clicked.connect(self._showConsole)
        self._buttonHideConsole.clicked.connect(self._hideConsole)
        self._buttonSaveOutput.clicked.connect(self._saveOutput)

        # Actions
        self._elements["actionOpen"].triggered.connect(self._openDialog)
        self._elements["actionClose"].triggered.connect(self._closeCurrentTab)
        self._actionExpand = self._elements["actionExpand"]
        self._actionExpandAll = self._elements["actionExpandAll"]
        self._actionCollapse = self._elements["actionCollapse"]
        self._actionCollapseAll = self._elements["actionCollapseAll"]

        # Console channel
        self._hideConsole()
        consoleChannelHelper = ConsoleChannelHelper(textEdit=self._textEdit)
        channels.add(ConsoleChannel, "_ui_console",
                     console=consoleChannelHelper)
        self._splitterConsole.handle(1).setEnabled(False)

        # Tab channel
        self._resultChannelHelper = ResultChannelHelper(self)
        channels.add(ResultChannel, "_ui_result",
                     result=self._resultChannelHelper)

# Slots:
    #@QtCore.Slot()
    def _openDialog(self):
        '''
        Opens selected files containing test results in tabs.
        '''
        log.debug("Opening result file")
        readableChannels = {}
        for c in [c for c in channels.get()
                    if isinstance(c, channels.TestResultFileChannel)]:
            desc = "%s (*.%s)" % (c.name, c.fileExt().strip("."))
            readableChannels[desc] = c
        if not readableChannels:
            dialogs.runWarning("There are no readable channels available")
            return
        dialog = QtGui.QFileDialog(self.view)
        dialog.setFileMode(QtGui.QFileDialog.ExistingFiles)
        dialog.setFilter(";;".join(readableChannels))
        if not dialog.exec_():
            log.debug("Opening result file was cancelled")
            return
        channel = readableChannels[dialog.selectedFilter()]
        for path in dialog.selectedFiles():
            try:
                self.addTab(channel.read(path), os.path.split(path)[1],
                            tooltip=path)
                self._updateRecentFiles(path)
            except Exception, ex:
                dialogs.runError("Error occurred while loading result file "
                                 "'%s':\n%s" % (path, ex))

    #@QtCore.Slot()
    def _openRecent(self):
        '''
        Opens a recent file containing test results in tabs.
        '''
        log.debug("Opening recent result file")

        path = self.sender().data()
        ext = os.path.splitext(path)[1]
        channel = None
        for c in channels.get():
            if (isinstance(c, channels.TestResultFileChannel) and
                c.fileExt() == ext):
                channel = c
                break
        if not channel:
            dialogs.runWarning("There are no readable channels accepting "
                               "'%s' files" % ext)
            return
        try:
            self.addTab(channel.read(path), os.path.split(path)[1],
                        tooltip=path)
        except Exception, ex:
            dialogs.runError("Error occurred while loading result file:\n%s"
                             % str(ex))

    #@QtCore.Slot(int)
    def _closeTabOfIndex(self, index):
        '''
        Closes a tab with test results of given index.
        '''
        title = self._tabWidget.tabText(index)
        if self._tabs[title].isClosable():
            log.debug("Closing result tab '%s'" % title)
            self._tabWidget.removeTab(index)
            del self._tabs[title]
        else:
            dialogs.runWarning("Result tab cannot be closed until the execution"
                               " of test cases is finished")

    #@QtCore.Slot()
    def _closeCurrentTab(self):
        '''
        Closes the current tab with test results.
        '''
        current = self._tabWidget.currentWidget()
        if current is not None:
            index = self._tabWidget.indexOf(current)
            self._closeTabOfIndex(index)

    #@QtCore.Slot(int)
    def _displaySelected(self, index):
        '''
        Displays information about currently selected item in the tab of
        given index.
        '''
        log.debug("Tab changed, displaying new item")
        tab = self._tabWidget.widget(index)
        self.clearDetails()
        for res in self._tabs.values():
            if res.tab == tab:
                res.refresh()
                break

    #@QtCore.Slot()
    def _showConsole(self):
        '''
        Shows the console widget.
        '''
        if not self._widgetConsole.isVisible():
            log.debug("Showing console output")
            self._widgetConsole.setVisible(True)
            self._buttonShowConsole.setVisible(False)
            self._buttonHideConsole.setVisible(True)
            self._splitterConsole.handle(1).setEnabled(True)

    #@QtCore.Slot()
    def _hideConsole(self):
        '''
        Hides the console widget.
        '''
        if self._widgetConsole.isVisible():
            log.debug("Hiding console output")
            self._widgetConsole.setVisible(False)
            self._buttonShowConsole.setVisible(True)
            self._buttonHideConsole.setVisible(False)

    #@QtCore.Slot()
    def _saveOutput(self):
        '''
        Saves console output to a selected file.
        '''
        log.debug("Saving console output")
        path = dialogs.runSaveFile("Text files (*.txt);;All files (*)")
        if path is None:
            return
        try:
            summary = open(path, "w")
            summary.write(self._textEdit.toPlainText())
            summary.close()
        except EnvironmentError, ex:
            dialogs.runError("Error occurred while writing to file %s:\n%s"
                             % (path, ex[1]))

    #@QtCore.Slot()
    def _updateRecentFiles(self, path=None):
        '''
        Rebuilds the Recent Files menu. If path is provided, it will be
        included as first item in the menu.
        '''
        log.debug("Updating recent files")
        if path is not None:
            self._recentFiles.add(path)
        for act in self._menuRecentFiles.actions():
            self._menuRecentFiles.removeAction(act)
        for i, path in enumerate(self._recentFiles.all()):
            dir, name = os.path.split(path)
            act = QtGui.QAction("&%d  %s [%s]" %(i+1, name, dir), self)
            act.setData(path)
            act.triggered.connect(self._openRecent)
            self._menuRecentFiles.addAction(act)
        self._menuRecentFiles.addSeparator()
        self._menuRecentFiles.addAction(self._actionClearMenu)

#Public methods
    def load(self):
        '''
        Loads the view and updates Recent Files menu.
        '''
        View.load(self)
        self._updateRecentFiles()

    def addTab(self, result, title, tooltip=None, select=False,
               closable=True):
        '''
        Creates and returns a tab containing a tree of test result items based
        on given result and title. Optional parameters are:
        - tooptip: a tooltip message of the tab, if not provided the title is
            used instead
        - select: a boolean that determines whether tree items should be
            selected while adding
        - closable: a boolean that determines if the tab can be closed manually
        '''
        log.debug("Adding tab: %s" % title)
        tab = ResultTab(self, result, select, closable)
        self._actionExpand.triggered.connect(tab.expand)
        self._actionExpandAll.triggered.connect(tab.expandAll)
        self._actionCollapse.triggered.connect(tab.collapse)
        self._actionCollapseAll.triggered.connect(tab.collapseAll)
        if title in self._tabs:
            remTab = self._tabs.pop(title)
            self._actionExpand.triggered.disconnect(remTab.expand)
            self._actionExpandAll.triggered.disconnect(remTab.expandAll)
            self._actionCollapse.triggered.disconnect(remTab.collapse)
            self._actionCollapseAll.triggered.disconnect(remTab.collapseAll)
            self._tabWidget.removeTab(self._tabWidget.indexOf(remTab.tab))
        index = self._tabWidget.addTab(tab.tab, title)
        self._tabWidget.setTabToolTip(index, tooltip or title)
        self._tabWidget.setCurrentWidget(tab.tab)
        self._tabs[title] = tab
        return tab

    def isTabCurrent(self, tab):
        '''
        Checks if given tab is the current tab in the tab widget.
        '''
        return self._tabWidget.currentWidget() == tab.tab

    def showLastResult(self):
        '''
        Makes the ResultChannel's tab current.
        '''
        tab = self._resultChannelHelper.getTab()
        index = self._tabWidget.indexOf(tab.tab)
        if index >= 0:
            log.debug("Changing current result tab to '%s'"
                      % self._tabWidget.tabText(index))
            self._tabWidget.setCurrentIndex(index)

    def showDetails(self, result):
        '''
        Displays details of the given test result.
        '''
        tree = self._treeWidget

        def makeItem(parent, name, value="", color=None, font=None,
                     expand=True, span=False):
            item = QtGui.QTreeWidgetItem(parent)
            nLabel = QtGui.QLabel(tree)
            nLabel.setText(utils.decode(name))
            item.setSizeHint(0, nLabel.sizeHint() + QtCore.QSize(10, 0))
            tree.setItemWidget(item, 0, nLabel)
            if font is not None:
                nLabel.setFont(font)
            if span:
                item.setFirstColumnSpanned(True)
            else:
                vLabel = QtGui.QLabel(tree)
                vLabel.setMinimumWidth(self._treeWidget.sizeHint().width() -
                                       self._treeWidget.columnWidth(0) - 1)
                tree.setItemWidget(item, 1, vLabel)
                if color:
                    vLabel.setText(u"<font color=\"%s\">%s</font>"
                                   % (color.color().name(),
                                      utils.decode(value)))
                else:
                    vLabel.setText(utils.decode(value))
                vLabel.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
                item.setSizeHint(1, QtCore.QSize(vLabel.sizeHint().width() + 10,
                                                 vLabel.sizeHint().height()))
            if expand:
                item.setExpanded(True)
            return item

        self.clearDetails()
        log.debug("Displaying selected tree item for result '%s'" % result.id)
        makeItem(tree, "Id", result.id)
        makeItem(tree, "Path", result.path)
        makeItem(tree, "Status", result.status,
                 color=STATUS_COLORS[result.status],
                 font=STATUS_FONTS[result.status])
        if result.attrs:
            item = makeItem(tree, "Attributes")
            for name, value in result.attrs.iteritems():
                makeItem(item, name, value)
        if isinstance(result, TestStepResult):
            makeItem(tree, "Function", result.func)
            if result.args:
                item = makeItem(tree, "Arguments")
                for name, value in result.args.iteritems():
                    makeItem(item, name, value)
        if result.devices:
            item = makeItem(tree, "Devices")
            for devResult in result.devices:
                devItem = makeItem(item, devResult.name, span=True)
                if devResult.description is not None:
                    makeItem(devItem, "Description", devResult.description)
                if devResult.address is not None:
                    makeItem(devItem, "Address", devResult.address)
                if devResult.port is not None:
                    makeItem(devItem, "Port", devResult.port)
                if devResult.status is not None:
                    makeItem(devItem, "Status", devResult.status,
                             color=STATUS_COLORS[devResult.status],
                             font=STATUS_FONTS[devResult.status])
                if devResult.errors:
                    errItem = makeItem(devItem, "Errors")
                    for error in devResult.errors:
                        makeItem(errItem, "", error)
                if devResult.cores:
                    coresItem = makeItem(devItem, "Cores")
                    for core in devResult.cores:
                        coreItem = makeItem(coresItem, core.path, expand=False,
                                            span=True)
                        makeItem(coreItem, "Size",
                                 "%s" % utils.sizeToString(core.size))
                        makeItem(coreItem, "Date",
                                 " ".join(utils.localTime(core.mtime)))
                if devResult.date:
                    makeItem(devItem, "Date",
                             utils.timeToString(devResult.date))
                if devResult.time:
                    makeItem(devItem, "Time", "%.6fs" % devResult.time)
        self._treeWidget.resizeColumnToContents(0)
        self._treeWidget.resizeColumnToContents(1)

    def clearDetails(self):
        '''
        Clears currently displayed details of a test result.
        '''
        self._treeWidget.clear()

    def saveState(self):
        '''
        Saves the view's settings to configuration.
        '''
        View.saveState(self)
        config.set(self.NAME, self._CONFIG_SECTION_CONSOLE,
                   "visible", self._widgetConsole.isVisible())

    def loadState(self):
        '''
        Loads the view's settings from configuration.
        '''
        View.loadState(self)
        visible = config.getBool(self.NAME, self._CONFIG_SECTION_CONSOLE,
                                 "visible", False)
        if self._widgetConsole.isVisible() != visible:
            if visible:
                self._showConsole()
            else:
                self._hideConsole()

