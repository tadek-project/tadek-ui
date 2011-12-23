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

import re
import string

from PySide import QtCore

from tadek.core import log
from tadek.core import config
from tadek.core import constants
from tadek.core.utils import decode

import utils
from dialogs import runWarning, runInformation


class SearchDialog(QtCore.QObject):
    '''
    A search dialog class.
    '''
    _SEARCH_UI = "search_dialog.ui"

    _DEEP_METHOD = 0
    _SIMPLE_METHOD = 1

    _PARTIAL_MATCH = 0
    _EXACT_MATCH = 1
    _REGULAR_EXPRESSION_MATCH = 2

    _CONFIG_NAME = "search"
    _CONFIG_SECTION_OPTIONS = "options"
    _CONFIG_SECTION_COMPLETERS = "completers"

    def __init__(self, view):
        QtCore.QObject.__init__(self)
        self.__dict__.update(view.loadUi(self._SEARCH_UI))
        self.buttonClose.clicked.connect(self.dialog.close)
        self.buttonSearch.clicked.connect(self._startSearching)
        self.buttonNext.clicked.connect(self._nextSearching)
        self.buttonStop.clicked.connect(self._stopSearching)
        self.dialog.finished.connect(self._onClose)

        self.comboBoxName.editTextChanged.connect(self._setName)
        self.comboBoxRole.editTextChanged.connect(self._setRole)
        self.comboBoxState.editTextChanged.connect(self._setState)
        self.plainTextEditText.textChanged.connect(self._setText)

        self.radioButtonDeep.clicked.connect(self._setDeepMethod)
        self.radioButtonSimple.clicked.connect(self._setSimpleMethod)

        self.checkBoxExactMatch.toggled.connect(self._setExactMatch)
        self.checkBoxCaseSensitive.toggled.connect(self._setCaseSensitiveMatch)

        self._view = view
        self._name = ''
        self._role = ''
        self._state = ''
        self._text = ''
        self._searching = False
        self._manualUpdate = False

        self._explorerDev = None
        self._foundAccessibles = []

        self.buttonNext.setVisible(False)
        self.buttonStop.setEnabled(False)

        self._lastNames = utils.LastValues(self._CONFIG_NAME,
                                           self._CONFIG_SECTION_COMPLETERS,
                                           "names")
        self._lastRoles = utils.LastValues(self._CONFIG_NAME,
                                           self._CONFIG_SECTION_COMPLETERS,
                                           "roles")
        self._lastStates = utils.LastValues(self._CONFIG_NAME,
                                            self._CONFIG_SECTION_COMPLETERS,
                                            "states")
        self.comboBoxName.completer().setCaseSensitivity(
            QtCore.Qt.CaseSensitive)
        self.comboBoxRole.completer().setCaseSensitivity(
            QtCore.Qt.CaseSensitive)
        self.comboBoxState.completer().setCaseSensitivity(
            QtCore.Qt.CaseSensitive)

    #@QtCore.Slot(str)
    def _setName(self, name):
        '''
        Sets the name of searched widgets.
        '''
        if self._manualUpdate:
            return
        self._stopSearching()
        self._name = decode(name).strip()

    #@QtCore.Slot(str)
    def _setRole(self, role):
        '''
        Sets the role of searched widgets.
        '''
        if self._manualUpdate:
            return
        self._stopSearching()
        self._role = decode(role).strip()

    #@QtCore.Slot(str)
    def _setState(self, state):
        '''
        Sets the state of searched widgets.
        '''
        if self._manualUpdate:
            return
        self._stopSearching()
        self._state = decode(state).strip()

    #@QtCore.Slot()
    def _setDeepMethod(self):
        '''
        Sets the deep method of widgets searching.
        '''
        self._stopSearching()
        self._method = self._DEEP_METHOD
        self._saveState()

    #@QtCore.Slot()
    def _setSimpleMethod(self):
        '''
        Sets the simple method for widgets searching.
        '''
        self._stopSearching()
        self._method = self._SIMPLE_METHOD
        self._saveState()

    #@QtCore.Slot()
    def _setText(self):
        '''
        Sets text of searched widgets.
        '''
        self._stopSearching()
        self._text = decode(self.plainTextEditText.toPlainText()).strip()
        self._saveState()

    #@QtCore.Slot()
    def _setExactMatch(self, checked):
        '''
        Sets the exact match for widgets searching.
        '''
        self._stopSearching()
        if checked:
            self._matchType = self._EXACT_MATCH
        else:
            self._matchType = self._PARTIAL_MATCH
        self._saveState()

    #@QtCore.Slot(bool)
    def _setCaseSensitiveMatch(self, checked):
        '''
        Sets the case sensitive match for widgets searching.
        '''
        self._stopSearching()
        self._caseSensitiveMatch = checked
        self._saveState()

    #@QtCore.Slot()
    def _onClose(self):
        '''
        Stops the searching process.
        '''
        self._stopSearching()

    #@QtCore.Slot()
    def _stopSearching(self):
        '''
        Stops the searching process and resets buttons.
        '''
        self.searchingStoppedUpdateState()  
        if self._searching:
            self._explorerDev.stopSearching()
            self._explorerDev.startItemChanged.disconnect(
                self._startItemChanged)
            self._explorerDev.itemFound.disconnect(self.itemFoundUpdateState)
            self._explorerDev.itemNotFound.disconnect(
                self.itemNotFoundUpdateState)
            self._explorerDev.searchingStopped.disconnect(self._stopSearching)
            self._searching = False

    class Check(object):
        '''
        Tests whether the given accessible matches the current search criteria.
        '''
        def __init__(self, criteria):
            '''
            Initializes the criteria for searching which should be provided
            as a dictionary with keys: name, role, text, type
            '''
            self.name = criteria['name'] or ''
            self.role = criteria['role'] or ''
            self.state = criteria['state'] or ''
            self.text = criteria['text'] or ''
            self._matchType = criteria['matchType']
            self._caseSensitiveMatch = criteria['caseSensitiveMatch']
            if self._matchType == SearchDialog._EXACT_MATCH:
                if not self._caseSensitiveMatch:
                    self.name = self.name.upper()
                    self.text = self.text.upper()
                    self.role = self.role.upper()
                    self.state = self.state.upper()
                self._matchName = lambda s: not self.name or s == self.name
                self._matchRole = lambda s: not self.role or s == self.role
                self._matchState = lambda s: not self.state or self.state in s
                self._matchText = lambda s: not self.text or s == self.text
            else:
                flags = re.DOTALL
                if not self._caseSensitiveMatch:
                    flags |= re.IGNORECASE
                # name
                if self.name and self.name[0] == '&':
                    self.name = self.name[1:]
                    compiledCriteriaName = self._compileExpression(
                        self.name+'\Z', flags, 'name')
                    self._matchName = lambda s: compiledCriteriaName.match(s)
                else:
                    if not self._caseSensitiveMatch:
                        self.name = self.name.upper()
                    self._matchName = lambda s: (not self.name or
                        s.find(self.name)>=0)
                # role
                if self.role and self.role[0] == '&':
                    self.role = self.role[1:]
                    compiledCriteriaRole = self._compileExpression(
                        self.role+'\Z', flags, 'role')
                    self._matchRole = lambda s: compiledCriteriaRole.match(s)
                else:
                    if not self._caseSensitiveMatch:
                        self.role = self.role.upper()
                    self._matchRole = lambda s: (not self.role or
                        s.find(self.role)>=0)
                # state
                if self.state and self.state[0] == '&':
                    self.state = self.state[1:]
                    compiledCriteriaState = self._compileExpression(
                        self.state+'\Z', flags, 'state')
                    
                    def matchState(s):
                        for state in s:
                            if compiledCriteriaState.match(state):
                                return True
                        return False
                    
                    self._matchState = matchState
                else:
                    if not self._caseSensitiveMatch:
                        self.state = self.state.upper()
                    
                    def matchState(s):
                        if not self.state:
                            return True
                        for state in s:
                            if state.find(self.state)>=0:
                                return True
                        return False
                    
                    self._matchState = matchState
                # text
                if self.text and self.text[0] == '&':
                    self.text = self.text[1:]
                    compiledCriteriaText = self._compileExpression(
                        self.text+'\Z', flags, 'text')
                    self._matchText = lambda s: compiledCriteriaText.match(s)
                else:
                    if not self._caseSensitiveMatch:
                        self.text = self.text.upper()
                    self._matchText = lambda s: (not self.text or
                        s.find(self.text)>=0)

        def __call__(self, itemData):
            '''
            Compares the data in provided dictionary with the criteria.
            '''
            itemName = itemData['name'] or ''
            itemRole = itemData['role'] or ''
            itemStates = (itemData['states'] if itemData['states'] is not None
                         else [])
            itemText = itemData['text'] or ''

            if not self._caseSensitiveMatch:
                if self._matchType == SearchDialog._EXACT_MATCH:
                    itemName = itemName.upper()
                    itemRole = itemRole.upper()
                    itemStates = map(string.upper, itemStates)
                    itemText = itemText.upper()
                else:
                    if itemName and itemName[0] != '&':
                        itemName = itemName.upper()
                    if itemText and itemText[0] != '&':
                        itemText = itemText.upper()

            return (self._matchName(itemName) and
                self._matchRole(itemRole) and
                self._matchState(itemStates) and
                self._matchText(itemText))

        def _compileExpression(self, pattern, flags, toLog):
            '''
            Compiles regular expression provided as pattern to check its
            correctness (and remembers it) and logs a message on failure.
            '''
            msg = "Regular expression \"%s\" is incorrect"
            msgToLog = "Regular expression for %s is incorrect"
            try:
                return re.compile(pattern, flags)
            except:
                runWarning(msg % pattern[:-1], "Incorrect expression")
                log.warning(msgToLog, toLog)
                raise

    #@QtCore.Slot()
    def _startSearching(self):
        '''
        Starts the searching process.
        '''
        self.buttonNext.setVisible(True)
        self.buttonNext.setEnabled(False)
        self.buttonSearch.setVisible(False)
        self.buttonStop.setEnabled(True)

        explorerDev = self._view.deviceTabAtIndex()
        if explorerDev is None:
            runWarning("No device is connected.", "Search unavailable")
            self.searchingStoppedUpdateState()
            return

        currentPath = explorerDev.selectedItemPath()
        if currentPath:
            if not explorerDev.itemExists(currentPath):
                self.searchingStoppedUpdateState()
                return
        else:
            runInformation("No item is selected.", "Search unavailable")
            self.searchingStoppedUpdateState()
            log.warning("Search cannot be performed since no reference item"
                " is selected")
            return

        self._explorerDev = explorerDev
        self._explorerDev.startItemChanged.connect(self._startItemChanged)
        self._explorerDev.itemFound.connect(self.itemFoundUpdateState)
        self._explorerDev.itemNotFound.connect(self.itemNotFoundUpdateState)
        self._explorerDev.searchingStopped.connect(self._stopSearching)
        self._searching = True

        criteria = {
            'name': self._name,
            'role': self._role,
            'state': self._state,
            'text': self._text,
            'matchType': self._matchType,
            'caseSensitiveMatch': self._caseSensitiveMatch
        }
        deep = False
        if self._method == self._DEEP_METHOD:
            deep = True
        try:
            explorerDev.find(self.Check(criteria), deep)
            self._lastNames.add(self._name)
            if self._role:
                self._lastRoles.add(self._role)
            if self._state:
                self._lastStates.add(self._state)
            self._manualUpdate = True
            self._refreshCompleters()
            self._manualUpdate = False
            self._saveState()
        except:
            self._stopSearching()

    #@QtCore.Slot()
    def _nextSearching(self):
        '''
        Searches a next matching item.
        '''
        self.buttonNext.setEnabled(False)
        self.buttonSearch.setVisible(False)
        self.buttonStop.setEnabled(True)
        self._explorerDev.findNext()

    #@QtCore.Slot()
    def itemFoundUpdateState(self):
        '''
        Updates buttons after the item is found.
        '''
        self.buttonNext.setVisible(True)
        self.buttonNext.setEnabled(True)
        self.buttonNext.setDefault(True)
        self.buttonSearch.setVisible(False)
        self.buttonSearch.setDefault(False)
        self.buttonStop.setEnabled(False)

    #@QtCore.Slot()
    def itemNotFoundUpdateState(self):
        '''
        Updates buttons after the item is not found.
        '''
        self.buttonNext.setVisible(False)
        self.buttonNext.setDefault(False)
        self.buttonSearch.setVisible(True)
        self.buttonSearch.setEnabled(True)
        self.buttonSearch.setDefault(True)
        self.buttonStop.setVisible(True)
        self.buttonStop.setEnabled(False)
        runInformation("No items found.", "Search finished")

    #@QtCore.Slot()
    def searchingStoppedUpdateState(self):
        '''
        Updates buttons after the searching is stopped by the user.
        '''
        self.buttonNext.setVisible(False)
        self.buttonNext.setAutoDefault(False)
        self.buttonSearch.setVisible(True)
        self.buttonSearch.setEnabled(True)
        self.buttonSearch.setDefault(True)
        self.buttonStop.setVisible(True)
        self.buttonStop.setEnabled(False)

    #@QtCore.Slot(QtGui.QTreeWidgetItem, int)
    def _startItemChanged(self):
        '''
        Handles the event when the user changes the reference item
        '''
        self._stopSearching()
        log.info("User selected new reference item to search")

    def _refreshCompleters(self):
        '''
        Refreshes completers for combo boxes so they are synchronized with
        their last used values.
        '''
        self.comboBoxName.clear()
        for name in self._lastNames.all():
            self.comboBoxName.addItem(name)
            self.comboBoxName.clearEditText()
        if len(self._name):
            index = self.comboBoxName.findText(self._name)
            if index >= 0:
                self.comboBoxName.setCurrentIndex(index)
        self.comboBoxRole.clear()
        self.comboBoxRole.addItems(self._lastRoles.all())
        if self.comboBoxRole.count():
            self.comboBoxRole.insertSeparator(self.comboBoxRole.count()) 
        self.comboBoxRole.addItems(constants.ROLES)
        self.comboBoxRole.clearEditText()
        if len(self._role):
            index = self.comboBoxRole.findText(self._role)
            if index >= 0:
                self.comboBoxRole.setCurrentIndex(index)
        self.comboBoxState.clear()
        self.comboBoxState.addItems(self._lastStates.all())
        if self.comboBoxState.count():
            self.comboBoxState.insertSeparator(self.comboBoxState.count()) 
        self.comboBoxState.addItems(constants.STATES)
        self.comboBoxState.clearEditText()
        if len(self._state):
            index = self.comboBoxState.findText(self._state)
            if index >= 0:
                self.comboBoxState.setCurrentIndex(index)

    def _saveState(self):
        '''
        Saves the dialog state to configuration.
        '''
        config.set(self._CONFIG_NAME, self._CONFIG_SECTION_OPTIONS, 
                   "match_type", self._matchType)
        config.set(self._CONFIG_NAME, self._CONFIG_SECTION_OPTIONS,
                   "case_sensitive", self._caseSensitiveMatch)
        config.set(self._CONFIG_NAME, self._CONFIG_SECTION_OPTIONS,
                   "method", self._method)
        log.info("Search dialog state was saved to configuration")

    def _loadState(self):
        '''
        Loads the dialog state from configuration.
        '''
        self._matchType = config.getInt(self._CONFIG_NAME,
                                        self._CONFIG_SECTION_OPTIONS,
                                        "match_type", self._PARTIAL_MATCH)
        self._caseSensitiveMatch = config.getBool(self._CONFIG_NAME,
                                                  self._CONFIG_SECTION_OPTIONS,
                                                  "case_sensitive", False)
        self._method = config.getInt(self._CONFIG_NAME,
                                     self._CONFIG_SECTION_OPTIONS,
                                     "method", self._DEEP_METHOD)

        if self._matchType == self._EXACT_MATCH:
            self.checkBoxExactMatch.setChecked(True)
        elif self._matchType == self._PARTIAL_MATCH:
            self.checkBoxExactMatch.setChecked(False)

        self.checkBoxCaseSensitive.setChecked(self._caseSensitiveMatch)
        
        if self._method == self._DEEP_METHOD:
            self.radioButtonDeep.setChecked(True)
        elif self._method == self._SIMPLE_METHOD:
            self.radioButtonSimple.setChecked(True)

        self._refreshCompleters()
        log.info("Search dialog state was loaded from configuration")

# Public methods:
    def run(self):
        '''
        Resets and shows the Search dialog.
        '''
        self._loadState()
        self.comboBoxName.clearEditText()
        self.plainTextEditText.clear()
        self.dialog.show()

    def stop(self):
        '''
        Stops searching.
        '''
        self._stopSearching() 

