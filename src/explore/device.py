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
from tadek.core import utils
from tadek.core import settings
from tadek.core import accessible

import dialogs
from utils import viewName, setWait, resetWait
from devices import OfflineDevice


class HighlightableItem(QtGui.QTreeWidgetItem):
    '''
    Class of items that can be highlighted.
    '''

    section = settings.get(viewName(), "highlight", force=True)
    _enabled = section.get("enabled", default="Yes")
    _mode = section.get("mode", default="selection")
    _red = section.get("red", default=0)
    _green = section.get("green", default=255)
    _blue = section.get("blue", default=255)
    _shading = section.get("shading", default=5)
    del section

    @classmethod
    def isHightlightEnabled(cls):
        '''
        Returns True if the highlight feature is enabled in settings. 
        '''
        return cls._enabled.getBool()

    @classmethod
    def hightlightMode(cls):
        '''
        Returns the highlight mode.
        '''
        return cls._mode.get().lower()

    def __init__(self, *args, **kwargs):
        QtGui.QTreeWidgetItem.__init__(self, *args, **kwargs)
        self._colorized = False
        mode = self.hightlightMode()
        
        if self.isHightlightEnabled() and mode in ("all", "selection"):
            if not self.parent() and mode == "all":
                self.setColor()
            else:
                self.updateColor()

    def resetColor(self):
        '''
        Changes background color of an item to transparent.
        '''
        self._colorized = False
        for i in range(self.treeWidget().columnCount()):
            self.setBackground(i, QtCore.Qt.transparent)

    def setColor(self):
        '''
        Highlights an item.
        '''
        self._colorized = True
        color = QtGui.QColor()                   
        color.setRed(self._red.getInt())
        color.setGreen(self._green.getInt())
        color.setBlue(self._blue.getInt())
        for i in range(self.treeWidget().columnCount()):
            self.setBackground(i, color)

    def updateColor(self):
        '''
        Makes an item highlighted using a slightly darker color than
        its parent is.
        '''
        step = self._shading.getInt()
        if self.parent() and self.parent().isColorized():
            self._colorized = True
            c = self.parent().background(0).color().darker(100 + step)
            for i in range(self.treeWidget().columnCount()):
                self.setBackground(i, c)

    def isColorized(self):
        '''
        Returns True if item setColor() was called or False otherwise.
        '''
        return self._colorized


class DeviceTab(QtCore.QObject):
    '''
    A device tab class.
    '''
    _DEVICE_TAB_UI = "device_tab.ui"
    _TIMEOUT_REFRESH = 10000
    _TIMEOUT_EXPAND = 300000
    _TIMEOUT_EXPAND_ALL = 600000
    _TIMEOUT_DUMP = 300000
    _TIMEOUT_DUMP_ALL = 600000
    _COLUMN_COUNT = 4
    
    itemFound = QtCore.Signal()
    itemNotFound = QtCore.Signal()
    startItemChanged = QtCore.Signal()
    searchingStopped = QtCore.Signal()

    def __init__(self, device, view):
        QtCore.QObject.__init__(self)
        self._offline = isinstance(device, OfflineDevice)
        self._manualExpand = False
        self._manualSelect = False
        self._reqMap = {}
        self._progressMap = {}
        self._view = view
        elements = view.loadUi(self._DEVICE_TAB_UI)
        self._treeWidget = elements["treeWidget"]
        self.device = device
        self.tab = elements["Tab"]
        self.tab.treeWidget.itemClicked.connect(self.startItemChanged)
        self._treeWidget.currentItemChanged.connect(self._updateHighlight) 
        self.setActive(True)

# Private methods:
    def _itemPath(self, item):
        '''
        Returns a path to the given accessible item.
        '''
        path = []
        parent = item.parent()
        while parent:
            path.insert(0, parent.indexOfChild(item))
            item = parent
            parent = item.parent()
        path.insert(0, self._treeWidget.indexOfTopLevelItem(item))
        return accessible.Path(*path)

    def _pathItem(self, path):
        '''
        Returns an item corresponding to the given path.
        '''
        if not path.tuple:
            return self._treeWidget
        item = self._treeWidget.topLevelItem(path.tuple[0])
        for idx in path.tuple[1:]:
            item = item.child(idx)
            if not item:
                break
        return item

    def _accessibleItem(self, accessible, parent, recursive=False):
        '''
        Adds an accessible tree item to the given parent.
        '''
        item = HighlightableItem(parent)
        self._setAccessibleItem(accessible, item)
        if accessible.count:
            if recursive:
                try:
                    item.setExpanded(True)
                    for child in accessible.children():
                        self._accessibleItem(child, item, True)
                except ValueError:
                    pass
            else:
                item.setChildIndicatorPolicy(HighlightableItem.ShowIndicator)
        return item

    def _setAccessibleItem(self, accessible, item):
        '''
        Sets the given accessible tree item.
        '''
        item.setText(0, str(accessible.index))
        item.setText(1, accessible.name)
        item.setText(2, accessible.role)
        item.setText(3, str(accessible.count))
        if accessible.count:
            item.setChildIndicatorPolicy(HighlightableItem.ShowIndicator)
        else:
            item.setChildIndicatorPolicy(HighlightableItem.DontShowIndicator)

    def _disableAccessibleItem(self, item):
        '''
        Disables the given accessible tree item.
        '''
        item.takeChildren()
        for col in xrange(1, item.columnCount()):
            item.setText(col, '')
        item.setDisabled(True)

    def _registerRequest(self, id, handler, *args):
        '''
        Designates a handler for device response of given id.
        '''
        if id is not None:
            self._view.reqIds.add(id)
            self._reqMap[id] = (handler, args)

    def _runProgress(self, id, message, **kwargs):
        '''
        Runs a process dialog with the specified parameters.
        '''
        if id is not None:
            self._progressMap[id] = dialogs.runProgress(message, **kwargs)

    def _updateHighlight(self, current, previous):
        '''
        Updates background color of items in the tree.
        '''
        def _update(item):
            for i in xrange(item.childCount()):
                child = item.child(i) 
                child.updateColor()
                _update(child)

        def _reset(item):
            item.resetColor()
            for i in xrange(item.childCount()):
                _reset(item.child(i))

        for i in xrange(self._treeWidget.topLevelItemCount()):
            _reset(self._treeWidget.topLevelItem(i))

        if HighlightableItem.isHightlightEnabled():
            mode = HighlightableItem.hightlightMode()
            if mode == "all":
                for i in xrange(self._treeWidget.topLevelItemCount()):
                    item = self._treeWidget.topLevelItem(i) 
                    item.setColor()
                    _update(item)
            elif mode == "selection" and current:
                current.setColor()
                _update(current)
        QtGui.qApp.processEvents()

# Response handlers:
    def _responseAdd(self, response):
        '''
        Adds an item to the acccessible tree from the response.
        '''
        path = response.accessible.path
        log.debug("Adding accessible tree item: %s" % path)
        parent = path.parent()
        if parent.tuple:
            parent = self._pathItem(parent)
            if not parent:
                log.warning("Invalid accessible tree path: %s" % path)
                return False
        else:
            parent = self._treeWidget
        accessible = response.accessible
        if response.status:
            self._accessibleItem(accessible, parent)
        else:
            item = HighlightableItem(parent)
            item.setText(0, str(accessible.index))
            item.setDisabled(True)
        for i in xrange(self._COLUMN_COUNT):
            self._treeWidget.resizeColumnToContents(i)
        return True

    def _responseRefresh(self, response, expanded=False):
        '''
        Refreshes an accessible tree item from the response.
        '''
        path = response.accessible.path
        log.debug("Refreshing accessible tree item: %s" % path)
        accessible = response.accessible
        item = self._pathItem(path)
        if not item:
            # Top level items should not change
            parent = self._pathItem(path.parent())
            if not parent:
                log.warning("Invalid accessible tree path: %s" % path)
                return False
            item = self._accessibleItem(accessible, parent)
        if not response.status:
            self._disableAccessibleItem(item)
            return False
        else:
            item.setDisabled(False)
        # Update the item
        self._setAccessibleItem(accessible, item)
        # Checks if display the item in the view
        if self.selectedItemPath() == path:
            self._view.display(accessible)
        if expanded and item.isExpanded():
            for idx in xrange(accessible.count, item.childCount()):
                item.takeChild(idx)
            for idx in xrange(accessible.count):
                childPath = path.child(idx)
                id = self.device.requestDevice("requestAccessible",
                                               childPath, 0)
                self._registerRequest(id, self._responseRefresh, True)
                self._runProgress(id, "Refreshing path %s" % childPath,
                                  timeout=self._TIMEOUT_REFRESH)
        elif accessible.count and not item.childCount():
            HighlightableItem(item)
        return True

    def _responseRefreshAll(self, response):
        '''
        Adds a root item to the acccessible tree from the response.
        '''
        path = response.accessible.path
        accessible = response.accessible
        log.debug("Adding root accessible items")
        if not response.status:
            return False
        for idx in xrange(accessible.count):
            id = self.device.requestDevice("requestAccessible",
                                           path.child(idx), 0)
            self._registerRequest(id, self._responseAdd)
        for i in xrange(self._COLUMN_COUNT):
            self._treeWidget.resizeColumnToContents(i)
        return True

    def _responseExpand(self, response):
        '''
        Expands an accessible tree item from the response.
        '''
        path = response.accessible.path
        log.debug("Expanding accessible tree item: %s" % path)
        item = self._pathItem(path)
        if not item:
            log.warning("EXPAND: Invalid accessible tree path: %s" % path)
            return False
        if not response.status:
            return False
        accessible = response.accessible
        # Update the item
        self._setAccessibleItem(accessible, item)
        item.setDisabled(False)
        # Request for children
        for idx in xrange(accessible.count):
            id = self.device.requestDevice("requestAccessible",
                                           path.child(idx), 0)
            self._registerRequest(id, self._responseAdd)
        for i in xrange(self._COLUMN_COUNT):
            self._treeWidget.resizeColumnToContents(i)
        return True

    def _responseExpandAll(self, response):
        '''
        Expands an accessible tree item from the response recursively.
        '''
        path = response.accessible.path
        log.debug("Expanding accessible tree item recursively: %s" % path)
        if not response.status:
            return False
        accessible = response.accessible
        item = None
        if path.tuple:
            item = self._pathItem(path)
            if not item:
                log.warning("Invalid accessible tree path: %s" % path)
                return False
            # Update the item
            self._setAccessibleItem(accessible, item)
            item.setDisabled(False)
        else:
            self._treeWidget.clear()
        self._manualExpand = True
        if item:
            item.setExpanded(True)
        for child in accessible.children():
            self._accessibleItem(child, item or self._treeWidget,
                                 recursive=True)
        for i in xrange(self._COLUMN_COUNT):
            self._treeWidget.resizeColumnToContents(i)
        self._manualExpand = False
        return True

    def _responseChange(self, response):
        '''
        Status of text/value changing an accessible tree item.
        '''
        log.debug("Changing text/value accessible tree item.")
        return response.status

    def _responseAction(self, response):
        '''
        Status of action execution on accessible tree item.
        '''
        log.debug("Executing action on accessible tree item.")
        return response.status

    def _responseFind(self, response=None):
        '''
        Handles responses to requests sent by the search.
        '''
        def fillRemaining(response):
            item = self._accessibleItem(response.accessible, self._parentItem)
            for i in xrange(self._COLUMN_COUNT):
                self._treeWidget.resizeColumnToContents(i)
            self._remainingItems[str(response.accessible.path)] = item

        if self._stopSearching:
            self._manualExpand = False
            self._manualSelect = False
            self._treeWidget.setCurrentItem(self._lastDisplayedItem)
            self.searchingStopped.emit()
            return

        # handle the response
        if response is not None:
            acc = response.accessible
            if acc:
                sort = False
                if str(acc.path) in self._remainingItems:
                    self._parentItem.removeChild(
                        self._remainingItems.pop(str(acc.path)))
                    sort = True
                item = self._accessibleItem(acc, self._parentItem)
                if sort:
                    children = self._parentItem.takeChildren()
                    children.sort(lambda a, b: cmp(int(a.text(0)),
                                                   int(b.text(0))))
                    for index, child in enumerate(children):
                        self._parentItem.insertChild(index, child)
                for i in xrange(self._COLUMN_COUNT):
                    self._treeWidget.resizeColumnToContents(i)
                if acc.count:
                    self._parentAccs.append(acc)

                # check if an item matches the criteria
                itemData = {}
                itemData['name'] = acc.name
                itemData['role'] = acc.role
                itemData['states'] = acc.states
                itemData['text'] = acc.text
                if self._check(itemData):
                    self._lastDisplayedItem = item
                    self._manualExpand = False
                    self._manualSelect = False
                    self._treeWidget.setCurrentItem(item)
                    # fill remaining child-items
                    for i in xrange(acc.index + 1, self._parentAcc.count):
                        childPath = self._parentAcc.path.child(i)
                        if str(childPath) in self._remainingItems:
                            continue
                        id = self.device.requestDevice("requestAccessible",
                                                       childPath, 0)
                        self._registerRequest(id, fillRemaining)
                    self.itemFound.emit()
                    return
                self._view.clear()
                self._treeWidget.setCurrentItem(item)

        if ((self._nextIndex > 0 and self._nextIndex >= self._parentAcc.count)
           or (self._nextIndex == 0 and self._parentAcc.count == 0)):
            if not self._deep or not self._parentAccs:
                # finish the search
                self._manualExpand = False
                self._manualSelect = False
                self._treeWidget.setCurrentItem(self._lastDisplayedItem)
                self.itemNotFound.emit()
                return

            # change the parent item
            self._parentAcc = self._parentAccs.pop(0)
            self._nextIndex = 0
            self._parentItem = self._pathItem(self._parentAcc.path)
            self._parentItem.takeChildren()
            self._parentItem.setExpanded(True)
            self._remainingItems = {}

        # send request for next accessible
        path = self._parentAcc.path.child(self._nextIndex)
        self._nextIndex += 1
        id = self.device.requestDevice("requestAccessible",
                                       path, 0, **self._options)
        self._registerRequest(id, self._responseFind)

    def _responseSave(self, response, filePath):
        '''
        Expands an accessible tree item from the response recursively.
        '''
        try:
            log.debug("Saving response to file '%s'" % filePath)
            element = response.accessible.marshal()
            utils.saveXml(element, filePath)
            self._view.updateRecentFiles(filePath)
        except:
            dialogs.runError("Error occurred while saving dump to file '%s'"
                             % filePath)

# Slots:
    #@QtCore.Slot()
    def showAccessible(self):
        '''
        Shows an accessible represented by the selected tree item.
        '''
        if self._manualSelect:
            return
        path = self.selectedItemPath()
        if not path:
            return
        log.debug("Selecting device accessible item: %s" % self.device)
        id = self.device.requestDevice("requestAccessible",
                                       path, 0, all=True)
        self._registerRequest(id, self._responseRefresh)
        setWait(self._view.view)

    #@QtCore.Slot(HighlightableItem)
    def expandAccessible(self, item):
        '''
        Expands an accessible item.
        '''
        if self._manualExpand or not self._active:
            return
        log.debug("Expanding device accessible item: %s" % self.device)
        path = self._itemPath(item)
        self._disableAccessibleItem(item)
        id = self.device.requestDevice("requestAccessible", path, 0)
        self._registerRequest(id, self._responseExpand)
        setWait(self._view.view)

    #@QtCore.Slot(HighlightableItem)
    def collapseAccesible(self, item):
        '''
        Collapses an accessible item.
        '''
        log.debug("Collapsing device accessible item: %s" % self.device)
        policy = item.childIndicatorPolicy()
        items = self._treeWidget.selectedItems()
        if items and items[0] is not item and items[0].parent():
            parent = items[0].parent()
            while True:
                if parent is item:
                    self._view.clear()
                    break
                if parent is None:
                    break
                parent = parent.parent()
        item.takeChildren()
        item.setChildIndicatorPolicy(policy)
        for i in xrange(self._COLUMN_COUNT):
            self._treeWidget.resizeColumnToContents(i)

    #@QtCore.Slot()
    def refresh(self):
        '''
        Refreshes a selected accessible item.
        '''
        if not self._active:
            return
        path = self.selectedItemPath()
        if not (self._active and path):
            return
        log.debug("Refreshing device accessible item: %s" % self.device)
        id = self.device.requestDevice("requestAccessible", path, 0, all=True)
        self._registerRequest(id, self._responseRefresh, True)
        self._runProgress(id, "Refreshing path: %s" % path,
                          timeout=self._TIMEOUT_REFRESH)

    #@QtCore.Slot()
    def refreshAll(self):
        '''
        Refreshes all accessible trees.
        '''
        if not self._active:
            return
        log.debug("Refreshing device accessible tree: %s" % self.device)
        self._manualSelect = True
        self._treeWidget.clear()
        self._view.clear()
        path = accessible.Path()
        id = self.device.requestDevice("requestAccessible", path, 0)
        self._registerRequest(id, self._responseRefreshAll)
        self._runProgress(id, "Refreshing path: %s" % path,
                          timeout=self._TIMEOUT_REFRESH)
        self._manualSelect = False

    #@QtCore.Slot()
    def expand(self):
        '''
        Expands a selected accessible item recursively.
        '''
        if not self._active:
            return
        path = self.selectedItemPath()
        if not (self._active and path):
            return
        log.debug("Expanding device accessible item recursively: %s"
                   % self.device)
        self._disableAccessibleItem(self._treeWidget.selectedItems()[0])
        id = self.device.requestDevice("requestAccessible", path, -1)
        self._registerRequest(id, self._responseExpandAll)
        self._runProgress(id, "Expanding path: %s" % path,
                          timeout=self._TIMEOUT_EXPAND)

    #@QtCore.Slot()
    def expandAll(self):
        '''
        Expands all accessible items recursively.
        '''
        if not self._active:
            return
        log.debug("Expanding all accessible items recursively: %s"
                   % self.device)
        path = accessible.Path()
        id = self.device.requestDevice("requestAccessible", path, -1)
        self._registerRequest(id, self._responseExpandAll)
        self._runProgress(id, "Expanding path: %s" % path,
                          timeout=self._TIMEOUT_EXPAND_ALL)

    #@QtCore.Slot()
    def collapse(self):
        '''
        Collapses a selected accessible item.
        '''
        if not self._active:
            return
        path = self.selectedItemPath()
        if not (self._active and path):
            return
        log.debug("Collapsing accessible item: %s" % path)
        self._treeWidget.selectedItems()[0].setExpanded(False)

    #@QtCore.Slot()
    def collapseAll(self):
        '''
        Expands a selected accessible item recursively.
        '''
        if not self._active:
            return
        log.debug("Collapsing device accessible tree: %s" % self.device)
        for idx in xrange(self._treeWidget.topLevelItemCount()):
            self._treeWidget.topLevelItem(idx).setExpanded(False)

    #@QtCore.Slot()
    def changeText(self):
        '''
        Changes text of selected accessible item.
        '''
        if not self._active:
            return
        path = self.selectedItemPath()
        if not path:
            return
        log.debug("Changing text of device accessible item: %s" % self.device)
        text = self._view.accessibleText()
        id = self.device.requestDevice("requestSetAccessible", path, text=text)
        self._registerRequest(id, self._responseChange)
        id = self.device.requestDevice("requestAccessible", path, 0, all=True)
        self._registerRequest(id, self._responseRefresh, True)
        setWait(self._view.view)

    #@QtCore.Slot()
    def changeValue(self):
        '''
        Changes value of selected accessible item.
        '''
        if not self._active:
            return
        path = self.selectedItemPath()
        if not path:
            return
        log.debug("Changing value of device accessible item: %s" % self.device)
        value = self._view.accessibleValue()
        id = self.device.requestDevice("requestSetAccessible",
                                       path, value=value)
        self._registerRequest(id, self._responseChange)
        id = self.device.requestDevice("requestAccessible", path, 0, all=True)
        self._registerRequest(id, self._responseRefresh, True)
        setWait(self._view.view)

    #@QtCore.Slot(QtGui.QAbstractButton)
    def doAction(self, button):
        '''
        Executes action on selected accessible item.
        '''
        if not self._active:
            return
        path = self.selectedItemPath()
        if not path:
            return
        log.debug("Execution action %s of device accessible item: %s"
                  % (button.text(), self.device))
        action = str(button.text())
        id = self.device.requestDevice("requestDoAccessible", path, action)
        self._registerRequest(id, self._responseAction)
        id = self.device.requestDevice("requestAccessible", path, 0, all=True)
        self._registerRequest(id, self._responseRefresh, True)
        setWait(self._view.view)

    #@QtCore.Slot()
    def save(self):
        '''
        Sends a recursive request for accessible that will be dumped to file.
        '''
        if not self._active:
            return
        items = self._treeWidget.selectedItems()
        if not items:
            return
        path = self._itemPath(items[0])
        if not path:
            return
        filePath = dialogs.runSaveFile("XML files (*.xml);;All files (*)",
                                       items[0].text(1))
        if filePath is None:
            return
        log.debug("Dumping accessible %s to file '%s'" % (path, filePath))
        id = self.device.requestDevice("requestAccessible", path, -1, all=True)
        self._registerRequest(id, self._responseSave, filePath)
        self._runProgress(id, "Dumping path: %s" % path,
                          timeout=self._TIMEOUT_DUMP)

    #@QtCore.Slot()
    def saveAll(self):
        '''
        Sends a recursive request for root accessible that will be dumped
        to file.
        '''
        if not self._active:
            return
        filePath = dialogs.runSaveFile("XML files (*.xml);;All files (*)")
        if filePath is None:
            return
        path = accessible.Path()
        log.debug("Dumping accessible %s to file '%s'" % (path, filePath))
        id = self.device.requestDevice("requestAccessible", path, -1, all=True)
        self._registerRequest(id, self._responseSave, filePath)
        self._runProgress(id, "Dumping path: %s" % path,
                          timeout=self._TIMEOUT_DUMP_ALL)

# Public methods:
    def isActive(self):
        '''
        Returns True if the device tab is active or False otherwise.
        '''
        return self._active

    def isOffline(self):
        '''
        Returns True is the tab operates on an offline device
        or False otherwise.
        '''
        return self._offline

    def hasSection(self):
        '''
        Returns True if a tree item is selected or False otherwise.
        '''
        return len(self._treeWidget.selectedItems()) > 0

    def itemExists(self, path):
        '''
        Returns True if an item corresponding to the given path exists.
        '''
        if not path.tuple:
            return True
        item = self._treeWidget.topLevelItem(path.tuple[0])
        for idx in path.tuple[1:]:
            item = item.child(idx)
            if not item:
                break
        return item is not None

    def selectedItemPath(self):
        '''
        Returns a path to a selected accessible item.
        '''
        items = self._treeWidget.selectedItems()
        if not items:
            return None
        return self._itemPath(items[0])

    def find(self, check, deep):
        '''
        Initiates the searching process.
        '''
        if not self._active:
            dialogs.runWarning("Device is disconnected")
            self.searchingStopped.emit()
            return
        log.info("Searching started for name: \"%s\", role: \"%s\", state: "
                 "\"%s\", text: \"%s\", with deep option set to %s)"
                 % (check.name, check.role, check.state, check.text, deep))
        self._manualExpand = True
        self._manualSelect = True
        self._deep = deep
        self._check = check
        self._options = {
            "text":  len(check.text) > 0,
            "states":  len(check.state) > 0,
        }
        self._stopSearching = False
        self._nextIndex = 0
        self._parentAccs = []
        self._parentAcc = self.device.getAccessible(
            self.selectedItemPath(), 0)
        self._parentItem = self._pathItem(self._parentAcc.path)
        self._lastDisplayedItem = self._parentItem
        self._remainingItems = {}

        self._parentItem.takeChildren()
        if self._parentAcc.count:
            self._parentItem.setExpanded(True)
        self._responseFind()

    def findNext(self):
        '''
        Runs the searching process again after a match was found.
        '''
        if not self._active:
            dialogs.runWarning("Device is disconnected")
            self.searchingStopped.emit()
            return
        log.info("Searching for next match")
        self._manualExpand = True
        self._manualSelect = True
        self._responseFind()

    def stopSearching(self):
        '''
        Stops the searching process.
        '''
        log.info("Searching was stopped")
        self._stopSearching = True

    def setActive(self, active):
        '''
        Activates or deactivates the device tab.
        '''
        log.debug("%s device tab: %s"
                  % ("Activating" if active else "Deactivating",
                     self.device.name))
        if active:
            self._treeWidget.itemSelectionChanged.connect(self.showAccessible)
            self._treeWidget.itemExpanded.connect(self.expandAccessible)
            self._treeWidget.itemCollapsed.connect(self.collapseAccesible)
        else:
            self._treeWidget.itemSelectionChanged.disconnect(
                self.showAccessible)
            self._treeWidget.itemExpanded.disconnect(self.expandAccessible)
            self._treeWidget.itemCollapsed.disconnect(self.collapseAccesible)
        self._active = active
        self.refreshAll()

    def process(self, response):
        '''
        Processes the given device response.
        '''
        if response.id not in self._reqMap:
            return False
        handler = self._reqMap.pop(response.id)
        func, args = handler[0], handler[1]
        func(response, *args)
        progressId = self._progressMap.pop(response.id, None)
        if progressId is not None:
            dialogs.closeProgress(progressId)
        resetWait(self._view.view)
        return True

