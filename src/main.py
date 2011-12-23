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

import view
import about
import icons
import utils
import devices
import settings

class MainWindow(QtCore.QObject):
    '''
    A main window class.
    '''
    _MAIN_WINDOW_UI = "main_window.ui"
    _NAME = "main"
    _TOOLBAR_BUTTON_LETTERS = 8

    def __init__(self):
        QtCore.QObject.__init__(self)
        elements = utils.loadUi(self._MAIN_WINDOW_UI)
        self.window = elements["MainWindow"]
        # Binding Window's custom event handlers
        self.window.closeEvent = self.closeEvent
        self.centralWidget = elements["centralWidget"]
        # Menus
        self.menuFile = elements["menuFile"]
        elements["actionQuit"].triggered.connect(self.window.close)
        self._actionQuit = elements["actionQuit"]
        self.menuEdit = elements["menuEdit"]
        self._actionDevices = elements["actionDevices"]
        self.menuView = elements["menuView"]
        # Tool bars
        self.toolBarMain = elements["toolBarMain"]
        self.toolBarSwitch = elements["toolBarSwitch"]
        self.toolBarView = elements["toolBarView"]
        # Dialogs
        self.about = about.About()
        elements["actionAbout"].triggered.connect(self.about.run)
        self.devices = devices.DevicesDialog()
        elements["actionDevices"].triggered.connect(self.devices.run)
        self.settings = settings.SettingsDialog()
        elements["actionSettings"].triggered.connect(self.settings.run)
        # Views
        self._viewGroup = QtGui.QActionGroup(self.window)
        self._views = view.all(self)
        for i, obj in enumerate(self._views):
            self._viewGroup.addAction(obj.action)
            self.menuView.addAction(obj.action)
            self.toolBarSwitch.addAction(obj.action)
            obj.action.setShortcut("ALT+%d" % (i+1))
        # Uniform width of ToolBar buttons
        self._buttonWidth = QtGui.QFontMetrics(self.window.font()).width(
                                            'a' * self._TOOLBAR_BUTTON_LETTERS)
        for toolBar in (self.toolBarMain, self.toolBarSwitch):
            for action in toolBar.actions():
                if action.isSeparator():
                    continue
                toolBar.widgetForAction(action).setFixedWidth(self._buttonWidth)
        # Settings
        self._loadState()

# Window's event handlers (each one should be bind to self.window in __init__):
    def closeEvent(self, event):
        '''
        Does pending tasks before the window is closed.
        '''
        self._saveState()
        self.devices.unload()
        self.clean()
        event.accept()

# Private methods:
    def _addMenuItems(self, menu, lastAction, items):
        '''
        Inserts actions to given menu before given action.
        '''
        for item in items:
            if isinstance(item, QtGui.QAction):
                menu.insertAction(lastAction, item)
            elif isinstance(item, QtGui.QMenu):
                menu.insertMenu(lastAction, item)
            else:
                raise TypeError("Invalid type of menu item: %s"
                                 % item.__class__.__name__)

    def _removeMenuItems(self, menu, items):
        '''
        Removes items from given menu.
        '''
        for item in items:
            if isinstance(item, QtGui.QMenu):
                item = item.menuAction()
            elif not isinstance(item, QtGui.QAction):
                raise TypeError("Invalid type of menu item: %s"
                                 % item.__class__.__name__)
            menu.removeAction(item)

    def _loadState(self):
        '''
        Loads window's settings from configuration.
        '''
        log.debug("Loading main window's settings")
        if self._views:
            index = config.getInt(self._NAME, "views", "last", 0)
            view = self._views[0]
            try:
                view = self._views[index]
            except IndexError:
                log.error("Failed to load view #%d" % index)
            view.activate()

        section = "geometry"
        self.window.setGeometry(
            config.getInt(self._NAME, section, "window_x", 50),
            config.getInt(self._NAME, section, "window_y", 50),
            config.getInt(self._NAME, section, "window_w", 800),
            config.getInt(self._NAME, section, "window_h", 600))
        state = config.get(self._NAME, section, "window_state")
        if state:
            byteData = QtCore.QByteArray.fromBase64(state)
            self.window.restoreState(byteData)

    def _saveState(self):
        '''
        Saves window's settings to configuration.
        '''
        log.debug("Saving main window's settings")
        section = "geometry"
        last = 0
        for i, view in enumerate(self._views):
            if view.loaded:
                last = i
                break
        config.set(self._NAME, "views", "last", last)
        config.set(self._NAME, section, "window_x", self.window.geometry().x())
        config.set(self._NAME, section, "window_y", self.window.geometry().y())
        config.set(self._NAME, section, "window_w",
                   self.window.geometry().width())
        config.set(self._NAME, section, "window_h",
                   self.window.geometry().height())
        config.set(self._NAME, section, "window_state",
                   str(self.window.saveState().toBase64()))

# Public methods:
    def getView(self, name):
        '''
        Gets a view of the given name or None.
        '''
        for view in self._views:
            if view.NAME == name:
                return view
        return None

    def dockWidget(self, widget):
        '''
        Docks the given root widget of a view in the main window.
        '''
        self.centralWidget.layout().addWidget(widget)

    def undockWidget(self, widget):
        '''
        Undocks the given root widget of a view from the main window.
        '''
        self.centralWidget.layout().removeWidget(widget)


    def addMenuFileItems(self, *items):
        '''
        Adds the given items to the file menu.
        '''
        self._addMenuItems(self.menuFile, self._actionQuit, items)

    def removeMenuFileItems(self, *items):
        '''
        Removes the given items from the file menu.
        '''
        self._removeMenuItems(self.menuFile, items)

    def addMenuEditItems(self, *items):
        '''
        Adds the given items to the edit menu.
        '''
        self._addMenuItems(self.menuEdit, self._actionDevices, items)

    def removeMenuEditItems(self, *items):
        '''
        Removes the given items from the edit menu.
        '''
        self._removeMenuItems(self.menuEdit, items)

    def addMenuViewItems(self, *items):
        '''
        Adds the given items to the view menu.
        '''
        self._addMenuItems(self.menuView, self._views[0].action, items)

    def removeMenuViewItems(self, *items):
        '''
        Removes the given items from the view menu.
        '''
        self._removeMenuItems(self.menuView, items)

    def addToolBarItems(self, *items):
        '''
        Adds the given items to the view tool bar.
        '''
        # FIXME: use QtGui.QToolBar.widgetForAction() when PySide bugs related
        # to this method will be fixed
        def widgetForAction(act):
            QtGui.qApp.processEvents()
            for c in self.toolBarView.children():
                if (isinstance(c, QtGui.QToolButton) and
                    c.text() == act.text().replace("&", "")):
                        return c

        for item in items:
            if isinstance(item, QtGui.QAction):
                self.toolBarView.addAction(item)
                if item.isSeparator():
                    continue
                w = widgetForAction(item)
                if w is not None:
                    w.setFixedSize(self._buttonWidth, w.sizeHint().height())
            elif isinstance(item, QtGui.QMenu):
                first = item.actions()[0]
                self.toolBarView.addAction(first)
                w = widgetForAction(first)
                if w is not None:
                    w.setPopupMode(QtGui.QToolButton.MenuButtonPopup)
                    w.setFixedSize(self._buttonWidth + 20,
                                   w.sizeHint().height())
                    w.setMenu(item)
            else:
                raise TypeError("Invalid type of tool bar item: %s"
                                 % item.__class__.__name__)

    def removeToolBarItems(self, *items):
        '''
        Removes the given items from the view tool bar.
        '''
        for item in items:
            if isinstance(item, QtGui.QAction):
                self.toolBarView.removeAction(item)
            elif isinstance(item, QtGui.QMenu):
                self.toolBarView.removeAction(item.actions()[0])
            else:
                raise TypeError("Invalid type of tool bar item: %s"
                                 % item.__class__.__name__)

    def setTitle(self, title):
        '''
        Sets title of the main window
        '''
        self.window.setWindowTitle(title)

    def getStatusBar(self):
        '''
        Gets status bar of the main window
        '''
        return self.window.statusBar()

    def clean(self):
        '''
        Clean the main window from a currently loaded view.
        '''
        for view in self._views:
            if view.loaded:
                view.unload()
                break

    def run(self):
        '''
        Runs the main window.
        '''
        self.window.show()
        self.devices.firstRun()

