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

import icons
import dialogs
from view import View
from device import DeviceTab
from search import SearchDialog
from devices import OfflineDevice
from exploredialogs import MouseDialog, KeyboardDialog
from utils import window, viewName, LastValues, ClosableTabBar

class Explore(View):
    '''
    A view for exploring accessible widgets on multiple devices.
    '''
    NAME = viewName()
    _UI_FILE = "explore_view.ui"
    _ICON_FILE = ":/explore/icons/system-search.png"

    _CONFIG_SECTION_MENU = "menu"

    # Menus and Tool bar
    _menuFile = (
        "actionOpen",
        (
            "Recent &Files",
            "actionClearMenu"
        ),
        None,
        "actionSave",
        "actionSaveAll",
        None,
        "actionClose"
    )
    _menuEdit = (
        "actionSearch",
        None,
        "actionExpand",
        "actionExpandAll",
        "actionCollapse",
        "actionCollapseAll",
        None
    )
    _menuView = (
        "actionRefresh",
        "actionRefreshAll",
        None
    )
    _toolBar = (
        "actionOpen",
        (
            "actionSave",
            "actionSaveAll"
        ),
        "actionClose",
        None,
        (
            "actionExpand",
            "actionExpandAll"
        ),
        (
            "actionCollapse",
            "actionCollapseAll"
        ),
        (
            "actionRefresh",
            "actionRefreshAll"
        ),
        None,
        "actionSearch"
    )

    def __init__(self, parent):
        View.__init__(self, parent)
        self._tabWidget = self._elements["tabWidget"]
        self._tabWidget.currentChanged[int].connect(self._updateView)
        self._tabWidget.tabCloseRequested.connect(self._close)
        self._tabWidget.setTabBar(ClosableTabBar())
        self._actionRefresh = self._elements["actionRefresh"]
        self._actionRefreshAll = self._elements["actionRefreshAll"]
        self._actionExpand = self._elements["actionExpand"]
        self._actionExpandAll = self._elements["actionExpandAll"]
        self._actionCollapse = self._elements["actionCollapse"]
        self._actionCollapseAll = self._elements["actionCollapseAll"]
        self._actionSearch = self._elements["actionSearch"]
        self._actionSave = self._elements["actionSave"]
        self._actionSaveAll = self._elements["actionSaveAll"]
        self._actionOpen = self._elements["actionOpen"]
        self._actionClose = self._elements["actionClose"]
        self._actionOpen.triggered.connect(self._openDialog)
        self._actionClose.triggered.connect(self._close)

        # Recent files menu
        self._recentFiles = LastValues(self.NAME, self._CONFIG_SECTION_MENU,
                                       "recent", 5)
        self._actionClearMenu = self._elements["actionClearMenu"]
        self._menuRecentFiles = self._menuFile[1]
        self._actionClearMenu.triggered.connect(self._recentFiles.clear)
        self._actionClearMenu.triggered.connect(self.updateRecentFiles)

        self._tabs = {}
        self._offlineDevs = {}
        self._readOnly = False

        self.search = SearchDialog(self)
        self._actionSearch.triggered.connect(self.search.run)

        self._dialogs = {
            'keyboard': KeyboardDialog(self),
            'mouse': MouseDialog(self)
        }

        # widgets
        self._states = self._elements["listWidgetStates"]
        self._relations = self._elements["listWidgetRelations"]
        self._attributes = self._elements["treeWidgetAttributes"]
        self._text = self._elements["textEditText"]
        self._changeText = self._elements["buttonChangeText"]
        self._actions = self._elements["groupBoxActions"]
        self._actionButtons = QtGui.QButtonGroup(self)
        self._value = self._elements["spinBoxValue"]
        self._changeValue = self._elements["buttonChangeValue"]
        self._mouse = self._elements["buttonMouse"]
        self._keyboard = self._elements["buttonKeyboard"]
        self.clear()

# Private methods:
    def _addDeviceTab(self, device):
        '''
        Adds the device tab for given device.
        '''
        log.debug("Adding device tab: %s" % device)
        tab = DeviceTab(device, self)
        self._tabs[device] = tab
        index = self._tabWidget.addTab(tab.tab, device.name)
        address, port = device.address
        if port:
            tooltip = "%s:%d" % (address, port)
        else:
            tooltip = address
        self._tabWidget.setTabToolTip(index, tooltip)
        self._tabWidget.setCurrentIndex(index)
        self._actionRefresh.triggered.connect(tab.refresh)
        self._actionRefreshAll.triggered.connect(tab.refreshAll)
        self._actionExpand.triggered.connect(tab.expand)
        self._actionExpandAll.triggered.connect(tab.expandAll)
        self._actionCollapse.triggered.connect(tab.collapse)
        self._actionCollapseAll.triggered.connect(tab.collapseAll)
        if not tab.isOffline():
            self._actionSave.triggered.connect(tab.save)
            self._actionSaveAll.triggered.connect(tab.saveAll)
            self._actionButtons.buttonClicked.connect(tab.doAction)
            self._mouse.clicked.connect(self._callMouseDialog)
            self._keyboard.clicked.connect(self._callKeyboardDialog)

    def _removeDeviceTab(self, device):
        '''
        Removes the device tab associated with given device.
        '''
        tab = self._tabs.pop(device, None)
        if tab is None:
            return
        log.debug("Removing device tab: %s" % device)
        self._tabWidget.removeTab(self._tabWidget.indexOf(tab.tab))
        if tab.isOffline():
            self._offlineDevs.pop(device.address[0])

    def _setInfoActive(self, devTab):
        '''
        Enables or disables interactions with right panel based on the state
        of given device tab.
        '''
        if devTab.isOffline() or not devTab.isActive():
            log.debug("Disabling interactions with right panel")
            self._mouse.setEnabled(False)
            self._keyboard.setEnabled(False)
            self._readOnly = True
        else:
            log.debug("Enabling interactions with right panel")
            self._mouse.setEnabled(True)
            self._keyboard.setEnabled(True)
            self._readOnly = False

    def _open(self, path):
        '''
        Opens a dump in a new tab and returns True on success or False
        on failure.
        '''
        if path in self._offlineDevs:
            self._offlineDevs[path].disconnectDevice()
        try:
            dev = OfflineDevice(os.path.split(path)[1], file=path)
            dev.responseReceived.connect(lambda id:
                                         self._deviceResponseReceived(dev, id))
            dev.connected.connect(lambda: self._deviceConnected(dev))
            dev.disconnected.connect(lambda:
                                     self._deviceDisconnected(dev, False))
            log.debug("Connecting off-line device: %s" % dev.name)
            dev.connectDevice()
            self._offlineDevs[path] = dev
            return True
        except Exception, ex:
            dialogs.runError("Error occurred while loading dump:\n%s" % str(ex))
            return False

    def _deviceConnected(self, device):
        '''
        Creates a tab representing the connected device or activates an
        inactive device tab.
        '''
        if device in self._tabs:
            tab = self._tabs[device]
            tab.setActive(True)
            self._tabWidget.setCurrentIndex(self._tabWidget.indexOf(tab.tab))
            self._setInfoActive(tab)
        else:
            self._addDeviceTab(device)

    def _deviceDisconnected(self, device, error):
        '''
        Removes a tab representing the disconnected device. The error parameter
        can be set to True to indicate that the device was disconnected due
        to an error. 
        '''
        tab = self._tabs.get(device)
        if not tab:
            return
        if error and not dialogs.runQuestion("Do you want to close '%s' tab?"
                                              % (device.name)):
            tab.setActive(False)
            if self._tabWidget.currentWidget() == tab.tab:
                self._setInfoActive(tab)
        else:
            self._removeDeviceTab(device)
        tab.searchingStopped.emit()

    def _deviceResponseReceived(self, device, id):
        '''
        Processes the received device response of given ID.
        '''
        response = View._deviceResponseReceived(self, device, id)
        if response is None:
            return
        tab = self._tabs.get(device, None)
        if tab is not None:
            log.debug("Processing '%d' device response: %s"
                      % (response.id, device))
            tab.process(response)
        else:
            log.debug("Ignoring response %d since '%s' device tab does not "
                      "exist" % (response.id, device))

# Public methods:
    def load(self):
        '''
        Loads the view and updates Recent Files menu.
        '''
        View.load(self)
        self.updateRecentFiles()

    def display(self, accessible):
        '''
        Displays details of the given accessible.
        '''
        log.debug("Displaying accessible details: %s" % accessible.path)
        self.clear()
        self._elements["labelName"].setText(accessible.name)
        self._elements["labelDescription"].setText(accessible.description)
        self._elements["labelRole"].setText(accessible.role)
        self._elements["labelChildren"].setText(str(accessible.count))
        self._elements["labelPath"].setText(unicode(accessible.path))
        
        # position
        if accessible.position is not None:
            self._elements["labelPosition"].setText(str(accessible.position))
        
        # size
        if accessible.size is not None:
            self._elements["labelSize"].setText(str(accessible.size))
        
        # states
        if accessible.states:
            for state in accessible.states:
                self._states.addItem(state)
            self._elements["groupBoxStates"].show()
        
        # relations
        if accessible.relations:
            for relation in accessible.relations:
                item = QtGui.QListWidgetItem(self._relations)
                item.setText(relation.type)
                item.setData(QtCore.Qt.BackgroundRole,
                             QtGui.QBrush(QtCore.Qt.lightGray))
                self._relations.addItem(item)
                for target in relation:
                    self._relations.addItem(unicode(target))
            self._elements["groupBoxRelations"].show()
        
        # attributes
        if accessible.attributes:
            for attr in accessible.attributes:
                item = QtGui.QTreeWidgetItem(self._attributes)
                item.setText(0, attr)
                item.setText(1, accessible.attributes[attr])
            self._elements["groupBoxAttributes"].show()
        
        # actions
        if accessible.actions:
            bpr = 3 # buttons per row - amount of buttons in one row
            for idx, action in enumerate(accessible.actions):
                button = QtGui.QPushButton(action)
                button.setMaximumWidth(120)
                if self._readOnly:
                    button.setEnabled(False)
                self._actions.layout().addWidget(button, idx/bpr, idx%bpr)
                self._actionButtons.addButton(button)
            self._actions.show()
        
        # text
        if accessible.text is not None:
            self._text.setPlainText(accessible.text)
            if accessible.editable and not self._readOnly:
                self._text.setReadOnly(False)
                self._changeText.setEnabled(True)
                for tab in self._tabs.values():
                    if tab.tab == self._tabWidget.currentWidget():
                        try:
                            self._changeText.clicked.connect(tab.changeText,
                                QtCore.Qt.UniqueConnection)
                        except RuntimeError:
                            pass
                        break
            else:
                self._text.setReadOnly(True)
                self._changeText.setEnabled(False)
            self._elements["groupBoxText"].show()
        
        # value
        if accessible.value is not None:
            self._value.setValue(accessible.value)
            if self._readOnly:
                self._changeValue.setEnabled(False)
            else:
                self._changeValue.setEnabled(True)
                for tab in self._tabs.values():
                    if tab.tab == self._tabWidget.currentWidget():
                        try:
                            self._changeValue.clicked.connect(tab.changeValue,
                                QtCore.Qt.UniqueConnection)
                        except RuntimeError:
                            pass
                        break
            self._elements["groupBoxValue"].show()
        else:
            self._changeValue.setEnabled(True)

        # update coordinates in mouse dialog
        if (accessible.position is not None and accessible.size is not None
            and not self._readOnly):
            mouseX = accessible.position[0] + accessible.size[0]/2
            mouseY = accessible.position[1] + accessible.size[1]/2
            self._dialogs['mouse'].setCoordinates(mouseX, mouseY)

    def clear(self):
        '''
        Clears accessible details.
        '''
        log.debug("Clearing accessible details")
        self._elements["labelName"].setText("")
        self._elements["labelDescription"].setText("")
        self._elements["labelRole"].setText("")
        self._elements["labelChildren"].setText("")
        self._elements["labelPath"].setText("")
        self._elements["labelPosition"].setText("")
        self._elements["labelSize"].setText("")
        
        # states
        self._states.clear()
        self._elements["groupBoxStates"].hide()
        
        # relations
        self._relations.clear()
        self._elements["groupBoxRelations"].hide()
        
        # attributes
        self._attributes.clear()
        self._elements["groupBoxAttributes"].hide()
        
        # actions
        child = self._actions.layout().takeAt(0)
        # deleting previously created action buttons
        #http://www.qtforum.org/article/26815/removing-a-layout-please-help.html
        while child != None:
            child.widget().deleteLater()
            child = self._actions.layout().takeAt(0)
        self._actions.hide()
        for button in self._actionButtons.buttons():
            self._actionButtons.removeButton(button)
            
        # text
        self._text.setPlainText("")
        self._text.setReadOnly(True)
        self._changeText.setEnabled(False)
        try:
            self._changeText.clicked.disconnect()
        except RuntimeError:
            pass
        self._elements["groupBoxText"].hide()
        
        # value
        self._value.setValue(0)
        try:
            self._changeValue.clicked.disconnect()
        except RuntimeError:
            pass
        self._elements["groupBoxValue"].hide()
        
        # mouse dialog clear
        self._dialogs['mouse'].setCoordinates(0, 0)

    def deviceTabAtIndex(self, index=None):
        '''
        Returns device tab linked with tab of given index or device tab linked
        with currently selected tab if index is None.
        '''
        if index is None:
            tab = self._tabWidget.currentWidget()
        else:
            tab = self._tabWidget.widget(index)
        for device, devTab in self._tabs.iteritems():
            if devTab.tab == tab:
                log.debug("'%s' device at index %s" % (device, str(index)))
                return devTab
        return None

    def accessibleText(self):
        '''
        Returns text of currently selected accessible.
        '''
        return self._text.toPlainText()

    def accessibleValue(self):
        '''
        Returns value of currently selected accessible.
        '''
        return self._value.value()

# Slots:
    #@QtCore.Slot()
    def updateRecentFiles(self, path=None):
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

    #@QtCore.Slot(int)
    def _updateView(self, index):
        '''
        Updates information about currently selected accessible item on tab
        on the given position, hides keyboard and mouse dialogs if opened and
        stops searching.
        '''
        log.debug("Updating info about selected item, closing dialogs and "
                  "stopping search")
        self.search.stop()
        for dialog in self._dialogs.values():
            if dialog.dialog.isVisible():
                dialog.hide()
        self.clear()
        devTab = self.deviceTabAtIndex(index)
        if devTab is not None:
            self._setInfoActive(devTab)
            if devTab.isActive() and devTab.hasSection():
                devTab.showAccessible()

    #@QtCore.Slot()
    def _callKeyboardDialog(self):
        '''
        Shows keyboard event dialog which helps to execute keyboard events
        on devices.
        '''
        currentDevTab = self.deviceTabAtIndex()
        if currentDevTab is not None:
            if not self._dialogs['keyboard'].dialog.isVisible():
                self._dialogs['keyboard'].run(currentDevTab)
            
    #@QtCore.Slot()
    def _callMouseDialog(self):
        '''
        Shows mouse event dialog which helps to execute mouse events on devices.
        '''
        currentDevTab = self.deviceTabAtIndex()
        if currentDevTab is not None:
            if not self._dialogs['mouse'].dialog.isVisible():
                self._dialogs['mouse'].run(currentDevTab)
                
    #@QtCore.Slot()
    def _openDialog(self):
        '''
        Shows a dialog to open a dump in a new tab.
        '''
        path = QtGui.QFileDialog.getOpenFileName(window(),
                                filter="XML files (*.xml);;All files (*)")[0]
        if not path:
            return
        log.debug("Opening dump file: '%s'" % path)
        if self._open(path):
            self.updateRecentFiles(path)

    #@QtCore.Slot()
    def _openRecent(self):
        '''
        Opens a recent dump file in a new tab.
        '''
        path = self.sender().data()
        log.debug("Opening recent dump: '%s'" % path)
        self._open(path)

    #@QtCore.Slot()
    def _close(self, index=None):
        '''
        Disconnects a dump tab or a device tab of given index.
        '''
        if index is None:
            index = self._tabWidget.currentIndex()
        tab = self.deviceTabAtIndex(index)
        if tab is None:
            return
        if not tab.isActive():
            self._removeDeviceTab(tab.device)
            return
        if tab.isOffline():
            act, obj = "close", "dump file"
        else:
            act, obj = "disconnect", "device"
        if dialogs.runQuestion("Do you want to %s '%s' %s?"
                               % (act, tab.device.name, obj)):
            log.debug("Disconnecting device of '%s' tab" % tab.device.name)
            tab.device.disconnectDevice()

