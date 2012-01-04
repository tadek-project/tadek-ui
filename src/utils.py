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
import os
import sys
import inspect

from PySide import QtCore
from PySide import QtGui
from PySide.QtUiTools import QUiLoader

from tadek.core import log
from tadek.core import config
from tadek.core.utils import getDataPath
from tadek.engine.testexec import (STATUS_PASSED, STATUS_FAILED, STATUS_ERROR,
                                   STATUS_NO_RUN, STATUS_NOT_COMPLETED)

__all__ = ["STATUS_COLORS", "STATUS_FONTS", "window", "viewName",
           "importModule", "loadUi", "setWait", "resetWait", "LastValues"]

STATUS_COLORS = {
    STATUS_PASSED:          QtGui.QBrush(QtCore.Qt.darkGreen),
    STATUS_FAILED:          QtGui.QBrush(QtCore.Qt.red),
    STATUS_ERROR:           QtGui.QBrush(QtCore.Qt.red),
    STATUS_NO_RUN:          QtGui.QBrush(QtCore.Qt.gray),
    STATUS_NOT_COMPLETED:   QtGui.QBrush(QtCore.Qt.blue),
    None:                   QtGui.QBrush(QtCore.Qt.gray),
}

STATUS_FONTS = {
    STATUS_PASSED:          QtGui.QFont(),
    STATUS_FAILED:          QtGui.QFont(),
    STATUS_ERROR:           QtGui.QFont(None,
                                        weight=QtGui.QFont.Weight.Bold),
    STATUS_NO_RUN:          QtGui.QFont(),
    STATUS_NOT_COMPLETED:   QtGui.QFont(),
    None:                   QtGui.QFont(),
}

def window():
    '''
    Returns the application window.
    '''
    if QtGui.qApp:
        windows = filter(lambda w: isinstance(w, QtGui.QMainWindow),
                      QtGui.qApp.topLevelWidgets())
        return windows[0] if windows else None
    return None

def viewName():
    '''
    If called from a code inside a package containing an implementation of
    a view, returns name of that view.
    '''
    return os.path.basename(os.path.dirname(inspect.stack(0)[1][1]))

def importModule(module):
    '''
    Imports a module of the given name.
    '''
    __import__(module)
    return sys.modules[module]

# Placeholder for names of registered custom widgets
_customWidgets = []

def loadUi(file, dir=None, parent=None):
    '''
    Loads the given ui file and returns a dictionary containing all UI elements.
    '''
    elements = {}
    if dir:
        file = os.path.join(dir, file)
    try:
        loader = QUiLoader()
        path = getDataPath("designer", file)
        f = None
        try:
            f = open(path)
            content = f.read()
            m = re.search("\"py_(.+?)\"", content)
            if m:
                name = content[m.start()+1: m.end()-1]
                if name and name not in _customWidgets:
                    baseName = name[3:]
                    cls = type(name, (getattr(QtGui, baseName),), {})
                    loader.registerCustomWidget(cls)
                    _customWidgets.append(name)
        finally:
            if f is not None:
                f.close()
        widget = loader.load(path)
        widget.setParent(parent, widget.windowFlags())
        elements[widget.objectName()] = widget
        for child in widget.findChildren(QtCore.QObject, None):
            name = child.objectName()
            if not name or name.startswith("_") or name.startswith("qt_"):
                continue
            elements[name] = child
    except:
        log.exception("UI resource file '%s' couldn't be loaded" % file)
    return elements

# widget-cursor map for setWait and resetWait
_widgets = {}

def setWait(widget):
    '''
    Sets 'busy' cursor on a widget.
    '''
    if widget not in _widgets:
        _widgets[widget] = [widget.cursor(), 0]
        widget.setCursor(QtCore.Qt.BusyCursor)
    _widgets[widget][1] += 1

def resetWait(widget):
    '''
    Replaces the 'busy' cursor of a widget with default one. 
    '''
    if widget in _widgets:
        if _widgets[widget][1] == 1:
            widget.setCursor(_widgets.pop(widget)[0])
        else:
            _widgets[widget][1] -= 1


class LastValues(object):
    '''
    class for last values storage.
    '''

    def __init__(self, conf, section, option, max=10):
        '''
        Synchronizes the internal list of values with configuration.
        '''
        self._values = config.getList(conf, section, option, [])
        if len(self._values) > max:
            self._values = self._values[:max]
            config.set(conf, section, option, self._values)
        self._conf = conf
        self._section = section
        self._option = option
        self._max = max

# Public methods:
    def add(self, value):
        '''
        Adds a value to the internal list.
        '''
        if value in self._values:
            self._values.remove(value)
        self._values.insert(0, value)
        if len(self._values) > self._max:
            self._values.pop()
        config.set(self._conf, self._section, self._option, self._values)

    def all(self):
        '''
        Retrieves internal list of values.
        '''
        return self._values[:]

    def clear(self):
        '''
        Removes all values from internal list.
        '''
        del self._values[:]
        config.set(self._conf, self._section, self._option, self._values)


class ClosableTabBar(QtGui.QTabBar):
    '''
    TabWidget that allows closing tabs using middle mouse button click.

    '''
    def __init__(self):
        QtGui.QTabBar.__init__(self)
        self.setTabsClosable(True)

    def mouseReleaseEvent(self, event):            
        if event.button() == QtCore.Qt.MidButton:           
            self.tabCloseRequested.emit(self.tabAt(event.pos()))
        QtGui.QTabBar.mouseReleaseEvent(self, event)

