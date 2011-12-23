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
from tadek.core import config

import utils

class ViewError(Exception):
    '''
    The view base error class.
    '''
    pass

class ViewConfigError(ViewError):
    '''
    The view configuration error class.
    '''
    MESSAGE_PATTERN = "Invalid view configuration: %s"

    def __init__(self, view):
        ViewError.__init__(self, self.MESSAGE_PATTERN % view)


class View(QtCore.QObject):
    '''
    A base class of main window views.
    '''
    NAME = None
    _UI_FILE = None
    _ICON_FILE = None

    _CONFIG_SECTION_GEOMETRY = "geometry"

    # Menus and Tool bar
    _menuFile = ()
    _menuEdit = ()
    _menuView = ()
    _toolBar = ()

    # View action
    action = None
    loaded = False
    _stateLoaded = False

    def __init__(self, parent):        
        QtCore.QObject.__init__(self)
        self._parent = parent
        if not (self.NAME and self._UI_FILE and self._ICON_FILE):
            raise NotImplementedError
        elements = utils.loadUi(self._UI_FILE, self.NAME)
        self.view = elements["View"]
        self.action = QtGui.QAction(QtGui.QIcon(self._ICON_FILE),
                                    self.NAME.capitalize(), self.view)
        self.action.setCheckable(True)
        self.action.changed.connect(self._update)

        # prepare actions for menus and toolbar
        for attr in ("_menuFile", "_menuEdit", "_menuView", "_toolBar"):
            actions = []
            for item in getattr(self, attr):
                if isinstance(item, (list, tuple)):
                    if item and item[0] not in elements:
                        menu = QtGui.QMenu(item[0])
                        item = item[1:]
                    else:
                        menu = QtGui.QMenu(elements[item[0]].text())
                    menu.addActions(tuple(self._separator() if n is None
                                    else elements[n] for n in item))
                    actions.append(menu)
                else:
                    actions.append(self._separator() if item is None
                                   else elements[item])
            setattr(self, attr, tuple(actions))

        # set of device response IDs the view is responsible for reception of
        self.reqIds = set()

        # setup handling signals from devices
        parent.devices.connected.connect(self._deviceConnected)
        parent.devices.disconnected.connect(self._deviceDisconnected)
        parent.devices.requestSent.connect(self._deviceRequestSent)
        parent.devices.responseReceived.connect(self._deviceResponseReceived)
        self._elements = elements

# Slots
    #@QtCore.Slot()
    def _update(self):
        '''
        Updates the view.
        '''
        if self.action.isChecked():
            self._parent.clean()
            self.load()

    #@QtCore.Slot(Device)
    def _deviceConnected(self, device):
        '''
        A slot for handling the device connected signal in the view.
        '''
        pass

    #@QtCore.Slot(Device)
    def _deviceDisconnected(self, device, error):
        '''
        A slot for handling the device disconnected signal in the view.
        '''
        pass

    #@QtCore.Slot(Device, int)
    def _deviceRequestSent(self, device, id):
        '''
        A slot for handling the device request sent signal in the view.
        '''
        pass

    #@QtCore.Slot(Device, int)
    def _deviceResponseReceived(self, device, id):
        '''
        A slot for handling  the device response received signal in the view.
        '''
        if id not in self.reqIds:
            return None
        self.reqIds.remove(id)
        return device.getResponse(id)

# Private methods:
    def _separator(self):
        '''
        Creates a separator action.
        '''
        action = QtGui.QAction(self.view)
        action.setSeparator(True)
        return action

# Public methods:
    def activate(self):
        '''
        Activates the view.
        '''
        if not self.action.isChecked():
            self.action.toggle()

    def load(self):
        '''
        Loads the view to its parent.
        '''
        log.debug("Loading view: %s" % self.NAME)
        self._parent.addMenuFileItems(*self._menuFile)
        self._parent.addMenuEditItems(*self._menuEdit)
        self._parent.addMenuViewItems(*self._menuView)
        self._parent.addToolBarItems(*self._toolBar)
        self._parent.dockWidget(self.view)
        self._parent.setTitle(self.NAME.capitalize())
        if not self._stateLoaded:
            self.loadState()
            self._stateLoaded = True
        self.view.show()
        self.loaded = True

    def unload(self):
        '''
        Unload the view from its parent.
        '''
        log.debug("Unloading view: %s" % self.NAME)
        self.saveState()
        self._parent.removeMenuFileItems(*self._menuFile)
        self._parent.removeMenuEditItems(*self._menuEdit)
        self._parent.removeMenuViewItems(*self._menuView)
        self._parent.removeToolBarItems(*self._toolBar)
        self._parent.undockWidget(self.view)
        self._parent.setTitle('')
        self.view.hide()
        self.loaded = False

    def loadUi(self, file):
        '''
        Loads the given ui file.
        '''
        return utils.loadUi(file, self.NAME, self.view)

    def loadState(self):
        '''
        Loads the view's settings from configuration.
        '''
        log.debug("Loading settings of view: %s" % self.NAME)
        for name in filter(lambda name: name.lower().find("splitter") >= 0,
                           self._elements):
            state = config.get(self.NAME, self._CONFIG_SECTION_GEOMETRY,
                               name.lower())
            if state:
                state = QtCore.QByteArray.fromBase64(state)
                self._elements[name].restoreState(state)

    def saveState(self):
        '''
        Saves the view's settings to configuration.
        '''
        log.debug("Saving settings of view: %s" % self.NAME)
        for name in filter(lambda name: "splitter" in name, self._elements):
            config.set(self.NAME,  self._CONFIG_SECTION_GEOMETRY,
                       name.lower(),
                       str(self._elements[name].saveState().toBase64()))


# View classes registry
_views = []

def register(view):
    '''
    Registers a view class of the given module-class path.
    '''
    try:
        mdl, cls = view.rsplit('.', 1)
        mdl = utils.importModule(mdl)
        cls = getattr(mdl, cls)
    except (ValueError, ImportError, AttributeError), err:
        log.exception(err)
        raise ViewConfigError(view)
    if not issubclass(cls, View):
        raise ViewError("The view already registered: %s" % view)
    if cls not in _views:
        _views.append(cls)

def all(parent):
    '''
    Gets instances of all registered view classes for the given parent.
    '''
    return [cls(parent) for cls in _views]

