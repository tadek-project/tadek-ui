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

from tadek.core import constants
from tadek.core import config
from tadek.core import log

import dialogs
from utils import viewName

class MouseDialog(QtCore.QObject):
    '''
    A dialog class for executing mouse event.
    '''
    _DIALOG_UI = "mouseevent_dialog.ui"
    _MAX_COORD = 10000
    _MIN_COORD = 0

    def __init__(self, view):
        QtCore.QObject.__init__(self, view)
        self._elements = view.loadUi(self._DIALOG_UI)
        self.dialog = self._elements['dialog']
        # Coordinates
        self._x = self._elements['spinBoxX']
        self._x.setMinimum(self._MIN_COORD)
        self._x.setMaximum(self._MAX_COORD)
        self._y = self._elements['spinBoxY']
        self._y.setMinimum(self._MIN_COORD)
        self._y.setMaximum(self._MAX_COORD)
        # Events
        self._events = {
            self._elements['radioClick']: 'CLICK',
            self._elements['radioDouble']: 'DOUBLE_CLICK',
            self._elements['radioPress']: 'PRESS',
            self._elements['radioRelease']: 'RELEASE',
            self._elements['radioAbsolute']: 'ABSOLUTE_MOTION',
            self._elements['radioRelative']: 'RELATIVE_MOTION'
        }
        self._event = QtGui.QButtonGroup()
        self._event.buttonClicked.connect(self._switch)
        for event in self._events:
            self._event.addButton(event)
        # Buttons
        self._buttons = dict(zip((self._elements['radioLeft'],
                                  self._elements['radioMiddle'],
                                  self._elements['radioRight']),
                                 constants.BUTTONS))
        self._button = QtGui.QButtonGroup()
        for button in self._buttons:
            self._button.addButton(button)
        self._ok = self._elements['buttonBox'].button(QtGui.QDialogButtonBox.Ok)
        self._ok.clicked.connect(self._execute)
        self._deviceTab = None

# Slots:
    #@QtCore.Slot(QtGui.QAbstractButton)
    def _switch(self, button):
        '''
        Enables or disables dialog radio buttons related to the mouse button.
        '''
        if 'MOTION' in self._events[button]:
            self._elements['groupBoxButton'].setDisabled(True)
        else:
            self._elements['groupBoxButton'].setEnabled(True)

    #@QtCore.Slot()
    def _execute(self):
        '''
        Executes keyboard event based on key code and modifiers.
        '''
        log.info('Executing mouse event')
        path = self._deviceTab.selectedItemPath()
        if path is None:
            dialogs.runWarning("No accessible item is selected."
                               "Mouse events unavailable")
        else:
            x = int(self._x.value())
            y = int(self._y.value())
            button = self._buttons[self._button.checkedButton()]
            event = self._events[self._event.checkedButton()]
            self._deviceTab.device.requestDevice("requestMouseEvent",
                                                 path, x, y, button, event)

# Public methods:
    def run(self, deviceTab):
        '''
        Runs the mouse event dialog.
        '''
        log.debug("Running mouse event dialog")
        self._deviceTab = deviceTab
        self.dialog.show()

    def hide(self):
        '''
        Hides the mouse event dialog.
        '''
        log.debug("Hiding mouse event dialog")
        self.dialog.done(1)

    def setCoordinates(self, x, y):
        '''
        Sets the X,Y coordinates.
        '''
        self._x.setValue(min(max(x, self._MIN_COORD), self._MAX_COORD))
        self._y.setValue(min(max(y, self._MIN_COORD), self._MAX_COORD))


class KeyboardDialog(QtCore.QObject):
    '''
    A dialog class for executing keyboard event.
    '''
    _DIALOG_UI = "kbevent_dialog.ui"
    _UNICODE_PREFIX = 0x01000000
    _CONFIG_NAME = viewName()
    _CONFIG_SECTION = "modifier_keys"
    _MODIFIERS = {
        'Alt': constants.KEY_CODES['LEFT_ALT'],
        'Control': constants.KEY_CODES['LEFT_CONTROL'],
        'Shift': constants.KEY_CODES['LEFT_SHIFT'],
    }

    def __init__(self, view):
        QtCore.QObject.__init__(self, view)
        self._elements = view.loadUi(self._DIALOG_UI)
        self.dialog = self._elements['dialog']
        self._character = self._elements['comboBoxChar']
        self._keycode = self._elements['lineEditKeycode']
        self._addMod = self._elements['buttonAdd']
        self._removeMod = self._elements['buttonRemove']
        self._ok = self._elements['buttonBox'].button(QtGui.QDialogButtonBox.Ok)
        self._modifiers = self._elements['listWidget']
        self._addEditDialog = AddEditDialog(view)

        self._character.editTextChanged.connect(self._update)
        self._keycode.textEdited.connect(self._clearAndDisable)
        self._ok.clicked.connect(self._execute)
        self._addEditDialog.modifierAccepted.connect(self._addModifier)
        self._modifiers.setSortingEnabled(True)
        self._modifiers.itemActivated.connect(self._deselectItem)
        self._modifiers.itemSelectionChanged.connect(self._switchButtons)
        self._addMod.clicked.connect(self._showAddEditDialog)
        self._removeMod.clicked.connect(self._removeModifier)

        for name, code in constants.KEY_SYMS.iteritems():
            prettyName = ' '.join([s.capitalize() for s in name.split('_')])
            self._character.addItem(prettyName, userData=str(code))
        self._character.setCompleter(None)
        self._keycode.setValidator(QtGui.QIntValidator(self.dialog))
        for name in sorted(self._MODIFIERS):
            self._createItem(name, self._MODIFIERS[name])
        self._userModifiers = []
        for name in config.get(self._CONFIG_NAME, self._CONFIG_SECTION):
            code = config.getInt(self._CONFIG_NAME, self._CONFIG_SECTION, name)
            if code is not None and code not in self._userModifiers:
                self._createItem(name, code)
                self._userModifiers.append(name)
        self._deviceTab = None

# Slots:
    #@QtCore.Slot(unicode)
    def _update(self, string):
        '''
        Fills an entry field containing key code.
        '''
        if len(string) == 0:
            return

        self._ok.setEnabled(True)
        data = self._character.itemData(self._character.findText(string))
        if data is None:
            code = ord(string[-1])
            if code > 127: # not ASCII code
                code += self._UNICODE_PREFIX
            self._character.setEditText(string[-1])
            self._keycode.setText(str(code))
        else:
            self._keycode.setText(data)

    #@QtCore.Slot(unicode)
    def _clearAndDisable(self, string):
        '''
        Clears an entry filed with character/button name and disables
        OK button if there is no key code.
        '''
        self._ok.setEnabled(len(string) > 0)
        self._character.clearEditText()

    #@QtCore.Slot()
    def _execute(self):
        '''
        Executes keyboard event based on key code and modifiers.
        '''
        log.info('Executing keyboard event')
        path = self._deviceTab.selectedItemPath()
        if path is None:
            dialogs.runWarning("No accessible item is selected. ",
                               "Keyboard events unavailable")
        else:
            keycode = int(self._keycode.text())
            items = self._modifiers.findItems('', QtCore.Qt.MatchContains)
            mods = [self._itemData(item)[1] for item in items
                                    if item.checkState() == QtCore.Qt.Checked]
            self._deviceTab.device.requestDevice("requestKeyboardEvent",
                                                 path, keycode, mods)

    #@QtCore.Slot(unicode, int)
    def _addModifier(self, name, code):
        '''
        Adds modifier to the list.
        '''
        selected = self._modifiers.selectedItems()
        if name in self._MODIFIERS:
            dialogs.runWarning("Default modifier '%s' cannot be redefined"
                               % name)
            return
        if selected:
            self._setItemData(selected[0], name, code)
        elif name in self._userModifiers:
            if dialogs.runQuestion("Modifier '%s' already exists. Do you "
                                   "want to update it?" % name):
                item = self._modifiers.findItems(name,
                                                 QtCore.Qt.MatchExactly)[0]
                self._setItemData(item, name, code)
            else:
                return
        else:
            self._userModifiers.append(name)
            self._modifiers.scrollToItem(self._createItem(name, code))
        config.set(self._CONFIG_NAME, self._CONFIG_SECTION, name, code)

    #@QtCore.Slot()
    def _removeModifier(self):
        '''
        Removes modifier from the list.
        '''
        selected = self._modifiers.selectedItems()
        for item in selected:
            removed = self._modifiers.takeItem(self._modifiers.row(item))
            if removed:
                self._userModifiers.remove(removed.text())
                config.remove(self._CONFIG_NAME, self._CONFIG_SECTION,
                              removed.text())

    #@QtCore.Slot()
    def _showAddEditDialog(self):
        '''
        Shows dialog for adding/editing modifiers.
        '''
        selected = self._modifiers.selectedItems()
        name = code = None
        if selected:
            if self._itemData(selected[0])[0] in self._MODIFIERS:
                self._modifiers.clearSelection()
            else:
                name, code = self._itemData(selected[0])
        self._addEditDialog.run(name, code, self._addMod.text() == "Add")

    #@QtCore.Slot()
    def _deselectItem(self, item):
        '''
        Deselects item if selected.
        '''
        if item.isSelected():
            item.setSelected(False)

    #@QtCore.Slot()
    def _switchButtons(self):
        '''
        Switches button Add (modifier) to Edit (modifier) and vice versa
        depending on selected modifiers. Also disables/enables Add and Remove
        buttons.
        '''
        selected = self._modifiers.selectedItems()
        self._addMod.setDisabled(True)
        self._removeMod.setDisabled(True)
        if len(selected) > 0:
            self._addMod.setDisabled(False)
            if selected[0].text() in self._userModifiers:
                self._addMod.setText("Edit")
                self._removeMod.setDisabled(False)
            else:
                self._addMod.setText("Add")
        else:
            self._addMod.setText("Add")
            self._removeMod.setDisabled(False)

# Private methods:
    def _createItem(self, name, code):
        '''
        Creates and returns a list item.
        '''
        item = QtGui.QListWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable |
                      QtCore.Qt.ItemIsUserCheckable |
                      QtCore.Qt.ItemIsEnabled)
        item.setCheckState(QtCore.Qt.Unchecked)
        self._setItemData(item, name, code)
        self._modifiers.addItem(item)
        return item

    def _setItemData(self, item, name, code):
        '''
        Updates modifier name and code associated with an item.
        '''
        item.setText(name)
        item.setData(QtCore.Qt.UserRole, code)
        item.setToolTip("Code: %d" % code)

    def _itemData(self, item):
        '''
        Returns modifier name and code associated with an item.
        '''
        return item.text(), item.data(QtCore.Qt.UserRole)

# Public methods:
    def run(self, deviceTab):
        '''
        Runs the keyboard event dialog.
        '''
        log.debug("Running keyboard event dialog")
        self._deviceTab = deviceTab
        self.dialog.show()

    def hide(self):
        '''
        Hides the keyboard event dialog.
        '''
        log.debug("Hiding keyboard event dialog")
        self.dialog.done(1)


class AddEditDialog(QtCore.QObject):
    '''
    A dialog class for adding or editing modifier.
    '''
    _DIALOG_UI = "addedit_dialog.ui"

# Signals:
    modifierAccepted = QtCore.Signal(unicode, int)

    def __init__(self, view):
        QtCore.QObject.__init__(self, view)
        self._elements = view.loadUi(self._DIALOG_UI)
        self.dialog = self._elements['dialog']
        self._key = self._elements['lineEditKey']
        self._code = self._elements['lineEditCode']
        self._ok = self._elements['buttonBox'].button(QtGui.QDialogButtonBox.Ok)

        self._code.setValidator(QtGui.QIntValidator(self.dialog))

        self._code.textEdited.connect(self._changeOk)
        self._key.textEdited.connect(self._changeOk)
        self._ok.setDisabled(True)
        self._ok.clicked.connect(self._execute)

    #@QtCore.Slot(unicode)
    def _changeOk(self, text):
        '''
        Changes state of OK button to disabled or enabled depending on
        fulfilment of key and code entry fields.
        '''
        if len(text) == 0:
            self._ok.setDisabled(True)
        elif len(self._key.text()) > 0 and len(self._code.text()) > 0:
            self._ok.setEnabled(True)

    #@QtCore.Slot()
    def _execute(self):
        '''
        Emits signal containing modifier data.
        '''
        self.modifierAccepted.emit(self._key.text(), int(self._code.text()))

# Public methods:
    def run(self, name, code, editName):
        '''
        Shows the dialog.
        '''
        if name is not None and code is not None:
            self._key.setText(name)
            self._code.setText(str(code))
            self._ok.setEnabled(True)
        else:
            self._key.clear()
            self._code.clear()
        if editName:
            self.dialog.setWindowTitle("Add modifier")
            self._key.setEnabled(True)
            self._key.setFocus()
        else:
            self.dialog.setWindowTitle("Edit modifier")
            self._key.setEnabled(False)
            self._code.setFocus()
        self.dialog.show()

