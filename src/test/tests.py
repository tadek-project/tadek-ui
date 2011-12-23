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
from tadek.core import settings
from tadek.core import location
from tadek.engine.loader import TestLoader
from tadek.engine.testdefs import TestSuite, TestCase

from utils import window, viewName
from dialogs import runWarning, runQuestion
from testdialogs import LoadingErrorDialog


class TestItem(QtGui.QTreeWidgetItem):
    '''
    Class of test tree items.
    '''

    def __init__(self, *args, **kwargs):
        self.testName = kwargs.pop("testName", None) 
        QtGui.QTreeWidgetItem.__init__(self, *args, **kwargs)


class Tests(QtCore.QObject):
    '''
    Class for management of locations list, tests tree and models tree.
    '''
    _TESTCASES_DIR = "testcases"

    _CONFIG_NAME = viewName()
    _CONFIG_SECTION_LOCATIONS = "locations"
    _expandOnRefresh = settings.get(_CONFIG_NAME, "options",
                                    "expand_on_refresh", default="No",
                                    force=True)

    _ICONS = {
        "directory": QtGui.QIcon(":/test/icons/folder-grey.png"),
        "module":    QtGui.QIcon(":/test/icons/text-x-python.png"),
        "suite":     QtGui.QIcon(":/test/icons/source_moc.png"),
        "case":      QtGui.QIcon(":/test/icons/inode-blockdevice.png")
    }

    def __init__(self, locsTree, testsTree, modelsTree):
        '''
        Takes trees for locations, tests and models, initializes a test
        loader instance and loads default paths from configuration.
        '''
        QtCore.QObject.__init__(self)
        self._locsTree = locsTree
        self._testsTree = testsTree
        self._modelsTree = modelsTree
        self._locsTree.itemChanged.connect(self._updateLocations)
        self._testsTree.itemChanged.connect(self._updateCheckboxes)
        self._loader = TestLoader()
        self._loaded = False
        self._locItems = {}
        self.loadState()

# Private methods:
    def _addLocation(self, path):
        '''
        Adds a location and a corresponding item to the locations tree.
        Returns None on success or an error message on failure.
        '''
        if path in self._locItems:
            return
        location.add(path, enabled=False)
        item = QtGui.QTreeWidgetItem()
        item.setText(0, path)
        item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable |
                      QtCore.Qt.ItemIsSelectable)
        item.setCheckState(0, QtCore.Qt.Unchecked)
        self._locsTree.addTopLevelItem(item)
        self._locsTree.resizeColumnToContents(0)
        self._locItems[path] = item

    def _changeExpansionState(self, state, selected=True):
        '''
        Manipulates expansion states of items in the tests tree. If selected is
        True (default), then only selected items are affected.
        '''
        def expandWithChildren(item, state):
            item.setExpanded(state)
            for i in xrange(item.childCount()):
                expandWithChildren(item.child(i), state)

        if selected:
            for item in self._testsTree.selectedItems():              
                expandWithChildren(item, state)
        else:
            for i in xrange(self._testsTree.topLevelItemCount()): 
                expandWithChildren(self._testsTree.topLevelItem(i), state)
        self._testsTree.resizeColumnToContents(0)

    def _updateModels(self):
        '''
        Refreshes the models tree.
        '''
        self._modelsTree.clear()
        for name, path in location.getModels().iteritems():
            QtGui.QTreeWidgetItem(self._modelsTree, [name, path])
        self._modelsTree.resizeColumnToContents(0)
        self._modelsTree.resizeColumnToContents(1)

# Slots:
    #@QtCore.Slot()
    def addLocation(self):
        '''
        Adds an item to locations tree and enables it. A warning is displayed
        if path is invalid.
        '''
        path = QtGui.QFileDialog.getExistingDirectory(window())
        if not path:
            return
        log.debug("Adding test path '%s'" % path)
        message = self._addLocation(path)
        if message is not None:
            runWarning(message)
            return
        self._locItems[path].setCheckState(0, QtCore.Qt.Checked)

    #@QtCore.Slot()
    def removeLocation(self):
        '''
        Removes selected items from locations tree and refreshes
        the tests tree.
        '''
        items = self._locsTree.selectedItems()
        if not (items and 
                runQuestion("Are you sure you want to remove %s?\n\n %s"
                            % ("these locations" if len(items) > 1
                                                 else "this location",
                               "\n".join(item.text(0) for item in items)))):
            return
        for item in items:
            path = item.text(0)
            log.debug("Removing test path '%s'" % path)
            location.remove(path)
            self._locsTree.takeTopLevelItem(
                self._locsTree.indexOfTopLevelItem(item))
            self._locItems.pop(path)
        self.refresh()

    #@QtCore.Slot()
    def getCheckedTests(self):
        '''
        Loads checked tests cases and returns them in a list on success
        or None on failure.
        '''
        def findCheckedNames(tests, item):
            if item.checkState(0) == QtCore.Qt.Checked:
                tests.append(item.testName)
                return
            elif item.checkState(0) == QtCore.Qt.PartiallyChecked:
                for i in xrange(item.childCount()):
                    findCheckedNames(tests, item.child(i))
        
        names = []
        for i in xrange(self._testsTree.topLevelItemCount()):
            findCheckedNames(names, self._testsTree.topLevelItem(i))
        if not names:
            runWarning("Select some test cases first")
            return names
        tests, errors = self._loader.loadFromNames(*names)
        if errors:
            if self._loaded:
                dialog = LoadingErrorDialog("Errors occurred while loading "
                                            "test cases", errors)
                dialog.run()
                return []

        return tests

    #@QtCore.Slot()
    def refresh(self):
        '''
        Clears and fills the tests tree and the models tree with contents from
        currently enabled locations.
        '''
        def makeItem(parent):
            item = TestItem(parent)
            item.setFlags(QtCore.Qt.ItemIsEnabled |
                          QtCore.Qt.ItemIsUserCheckable |
                          QtCore.Qt.ItemIsSelectable)
            item.setCheckState(0, QtCore.Qt.Unchecked)
            return item

        def buildSuite(name, suite, parent):
            item = makeItem(parent)
            item.setText(0,
                         name if name is not None else suite.__class__.__name__)
            item.testName = ".".join((item.parent().testName, item.text(0)))
            if isinstance(suite, TestSuite):
                item.setIcon(0, self._ICONS["suite"])
                for name, childSuite in suite:
                    buildSuite(name, childSuite, item)
            elif isinstance(suite, TestCase):
                item.setIcon(0, self._ICONS["case"])
            else:
                raise TypeError()

        def buildTree(tree, parent):
            for key in sorted(tree):
                value = tree[key]
                if key is None and isinstance(value, list):
                    if not value and len(tree) == 1:
                        if parent.parent() is not None:
                            parent.parent().removeChild(parent)
                        else:
                            self._testsTree.takeTopLevelItem(
                                self._testsTree.indexOfTopLevelItem(parent))
                        continue
                    suite = None
                    for suite in value:
                        buildSuite(None, suite, parent)
                    if value:
                        r = suite.result()
                        if os.path.split(r.path)[1] != r.id.split(".")[-2]:
                            parent.setIcon(0, self._ICONS["module"])
                elif isinstance(value, dict):
                    item = makeItem(parent)
                    item.setText(0, key)
                    item.setIcon(0, self._ICONS["directory"])
                    item.testName = (".".join((item.parent().testName, key))
                                      if item.parent() is not None else key)
                    buildTree(value, item)

        self._testsTree.clear()
        tree, errors = self._loader.loadTree()
        if errors:
            if self._loaded:
                dialog = LoadingErrorDialog("Errors occurred while loading "
                                            "test cases", errors)
                dialog.run()
        buildTree(tree, self._testsTree)
        self._testsTree.resizeColumnToContents(0)
        if self._expandOnRefresh.getBool():
            self.expandAll()
        self._updateModels()

    #@QtCore.Slot()
    def expandSelected(self):
        '''
        Expands selected test items including all descendants.
        '''
        self._changeExpansionState(state=True, selected=True)

    #@QtCore.Slot()
    def expandAll(self):
        '''
        Expands all test items including all descendants.
        '''
        self._changeExpansionState(state=True, selected=False)

    #@QtCore.Slot()
    def collapseSelected(self):
        '''
        Collapses selected test items including all descendants.
        '''
        self._changeExpansionState(state=False, selected=True)

    #@QtCore.Slot()
    def collapseAll(self):
        '''
        Collapses all test items including all descendants.
        '''
        self._changeExpansionState(state=False, selected=False)

    #@QtCore.Slot(QtGui.QTreeWidgetItem, int)
    def _updateLocations(self, item, column):
        '''
        Enables or disables a location and refreshes the tests tree.
        '''
        if item.checkState(0) == QtCore.Qt.Checked:
            errors = location.enable(item.text(0))
            if errors:
                if self._loaded:
                    dialog = LoadingErrorDialog("Errors occurred while enabling"
                                                " a location", errors)
                    dialog.run()
                item.setCheckState(0, QtCore.Qt.Unchecked)
                return
        else:
            location.disable(item.text(0))
        self.refresh()

    #@QtCore.Slot(TestItem, int)
    def _updateCheckboxes(self, item, column):
        '''
        Updates states of check boxes in the tests tree in three-state manner. 
        '''
        def updateChildren(item, state):
            item.setCheckState(0, state)
            for i in xrange(item.childCount()):
                updateChildren(item.child(i), state)

        if item is not self._testsTree.currentItem():
            return
        updateChildren(item, item.checkState(0))
        parent = item.parent()
        while parent is not None:
            states = [parent.child(i).checkState(0)
                      for i in xrange(parent.childCount())]
            if (len(filter(lambda s: s == QtCore.Qt.Checked, states))
                == len(states)):
                state = QtCore.Qt.Checked
            elif (len(filter(lambda s: s == QtCore.Qt.Unchecked, states))
                  == len(states)):
                state = QtCore.Qt.Unchecked
            else:
                state = QtCore.Qt.PartiallyChecked
            parent.setCheckState(0, state)
            parent = parent.parent()

# Public methods:
    def saveState(self):
        '''
        Saves paths to configuration.
        '''
        config.set(self._CONFIG_NAME, self._CONFIG_SECTION_LOCATIONS,
                   "enabled", location.get(enabled=True))
        config.set(self._CONFIG_NAME, self._CONFIG_SECTION_LOCATIONS,
                   "disabled", location.get(enabled=False))

    def loadState(self):
        '''
        Restores paths from configuration.
        ''' 
        enabled = config.getList(self._CONFIG_NAME,
                                 self._CONFIG_SECTION_LOCATIONS,
                                 "enabled", [])
        disabled = config.getList(self._CONFIG_NAME,
                                  self._CONFIG_SECTION_LOCATIONS,
                                  "disabled", [])
        for path in disabled:
            message = self._addLocation(path)
            if message:
                log.warning(message)
        for path in enabled:
            message = self._addLocation(path)
            if message:
                log.warning(message)
            else:
                self._locItems[path].setCheckState(0, QtCore.Qt.Checked)
        self._loaded = True

