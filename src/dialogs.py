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
import re
import threading

from PySide import QtCore
from PySide import QtGui

from tadek.core import log

import utils

class ProgressDialog(QtGui.QProgressDialog):
    '''
    A progress dialog class.
    '''
    def __init__(self, parent=None):
        QtGui.QProgressDialog.__init__(self, parent=parent)
        self.setWindowModality(QtCore.Qt.WindowModal)
        self.setRange(0, 0)
        self.setCancelButtonText(None)
        self._dict = {}
        self._timeouts = {}
        self._id = -1
        self._current = -1
        self._lock = threading.RLock()

# Private methods:
    def _update(self):
        '''
        Displays the message with least timeout value.
        '''
        def compare(a, b):
            if a == b or (a is None and b is None):
                return 0
            elif a is None:
                return -1
            elif b is None:
                return 1
            elif a > b:
                return -1
            elif a < b:
                return 1

        ids = sorted(self._dict, cmp=compare,
                     key=lambda k: self._dict[k][2], reverse=True)
        if not ids:
            self.close()
            return
        elif ids[0] != self._current:
            title, message = self._dict[ids[0]][:2]
            self.setWindowTitle(title)
            self.setLabelText(message)
            self._current = ids[0]
        if not self.isVisible():
            self.show()

# Slots:
    #@QtCore.Slot()
    def _handleTimeout(self):
        '''
        Removes the message identified by ID of the sender.
        '''
        id = self.sender()._id
        message = self._dict[id][1]
        self.remove(id)
        runWarning("Timeout reached for operation:\n%s" % message)

# Public methods:
    def add(self, message, title, timeout=None):
        '''
        Adds a message and returns an ID.
        '''
        self._lock.acquire()
        try:
            id = self._id + 1
            timer = None
            if timeout is not None:
                timer = QtCore.QTimer(self)
                timer.setSingleShot(True)
                timer.setInterval(timeout)
                timer._id = id
                timer.timeout.connect(self._handleTimeout)
                timer.start()
            self._dict[id] = (title, message, timeout, timer)
            self._id = id
            self._update()
            return id
        finally:
            self._lock.release()

    def remove(self, id):
        '''
        Removes a message of given ID.
        '''
        self._lock.acquire()
        try:
            if id not in self._dict:
                return
            timer = self._dict.pop(id)[3]
            if timer and timer.isActive:
                timer.stop()
            self._update()
        finally:
            self._lock.release()

    def closeEvent(self, event):
        '''
        Prevents the dialog from closing unless there are no more messages. 
        '''
        if self._dict:
            event.ignore()

# instance of ProgressDialog
_progress = None

def runProgress(message, title="Wait", timeout=None):
    '''
    Enqueues a message to the progress dialog.
    
    :param message: Message to be displayed inside the dialog
    :type message: string
    :param title:  Title of the dialog
    :type title: string
    :param timeout: Timeout of the dialog in microseconds, the default value
        is infinity
    :type timeout: integer
    :return: Unique identifier of the message
    :rtype: integer
    '''
    global _progress
    if _progress is None:
        _progress = ProgressDialog(utils.window())
    return _progress.add(message, title, timeout)

def closeProgress(id):
    '''
    Removes a message from the progress dialog.
    
    :param id: Identifier of a message to remove
    :type id: integer
    '''
    _progress.remove(id)


def runError(message, title="Error"):
    '''
    Runs an error message box with the given title and message.
    
    :param message: Message to be displayed inside the dialog
    :type message: string
    :param title:  Title of the dialog, if not provided, "Error" is set
    :type title: string
    '''
    log.error(message)
    return QtGui.QMessageBox.critical(utils.window(), title, message)

def runWarning(message, title="Warning"):
    '''
    Runs an warning message box with the given title and message.
    
    :param message: Message to be displayed inside the dialog
    :type message: string
    :param title:  Title of the dialog, if not provided, "Warning" is set
    :type title: string
    '''
    log.warning(message)
    return QtGui.QMessageBox.warning(utils.window(), title, message)


def runInformation(message, title="Information"):
    '''
    Runs an information message box with the given title and message.
    
    :param message: Message to be displayed inside the dialog
    :type message: string
    :param title:  Title of the dialog, if not provided, "Information" is set
    :type title: string
    '''
    log.info(message)
    return QtGui.QMessageBox.information(utils.window(), title, message)

def runQuestion(message, title="Question"):
    '''
    Runs a question message box with the given title and message.
    
    :param message: Message to be displayed inside the dialog
    :type message: string
    :param title:  Title of the dialog, if not provided, "Question" is set
    :type title: string
    :return: Answer to a question
    :rtype: boolean
    '''
    btns = {QtGui.QMessageBox.Yes: True, QtGui.QMessageBox.No: False}
    b = reduce(QtGui.QMessageBox.StandardButton.__ror__, btns.keys())
    ret = btns[QtGui.QMessageBox.question(utils.window(), title, message, b)]
    log.info("%s: %s" % (message, ret))
    return ret

def runSaveFile(filters, name=""):
    '''
    Runs a save file dialog and returns a path or None.
    
    :param filters: Filters in QFileDialog format
    :type filters: string
    :param name: Default file name
    :type name: string
    :return: Path to a file or None
    :rtype: string
    '''
    dialog = QtGui.QFileDialog(utils.window())
    dialog.setAcceptMode(QtGui.QFileDialog.AcceptMode.AcceptSave)
    dialog.setFileMode(QtGui.QFileDialog.FileMode.AnyFile)
    dialog.setOption(QtGui.QFileDialog.DontConfirmOverwrite)
    
    extensions = {}
    for a in filters.split(";;"):
        m = re.search("\(\*(.*)\)", a)
        if not m:
            continue
        extensions[a] = m.group(1).strip(".")

    dialog.setFilter(filters)
    dialog.selectFile(name)
    if not dialog.exec_():
        return None
    path = dialog.selectedFiles()[0]
    ext = extensions[dialog.selectedFilter()] 
    if ext not in ("", "*") and os.path.splitext(path)[1].strip(".") != ext:
        path = "%s.%s" % (path, ext)
    if os.path.exists(path):
        if not runQuestion("'%s' already exists.\nDo you want to replace it?"
                           % os.path.split(path)[1]):
            return None
    dialog.setParent(None)
    return path

