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

from tadek.engine.channels import TestResultChannel
from tadek.engine.testexec import (STATUS_NO_RUN, STATUS_NOT_COMPLETED,
                                   STATUS_PASSED, STATUS_FAILED, STATUS_ERROR)

class ConsoleChannelHelper(QtCore.QObject):
    '''
    A helper class to interact with a console channel.
    It writes into a text edit widget.
    '''
    START_FORMAT = "[%(device.name)s] START %(result.id)s"
    STOP_FORMAT  = "[%(device.name)s] STOP  %(result.id)s %(device.status)s"

    RESULT_NAMES = {
        "TestStepResult":  "STEP",
        "TestCaseResult":  "TEST",
        "TestSuiteResult": "SUITE"
    }
    STATUS_STYLES = {
        STATUS_ERROR:         "color: red; font-weight: bold",
        STATUS_FAILED:        "color: red",
        STATUS_PASSED:        "color: green",
        STATUS_NOT_COMPLETED: "color: blue",
        STATUS_NO_RUN:        "color: gray"
    }

    _updated = QtCore.Signal(basestring)

    class _Mapper(dict):
        '''
        Gives access to attributes of object(s) by keys.
        '''
        def __init__(self, objects={}, subs={}):
            dict.__init__(self)
            self._objects = objects
            self._subs = subs

        def __getitem__(self, name):
            item = ''
            try:
                item = eval(name, {}, self._objects)
                if name in self._subs:
                    item = self._subs[name][item]
            finally:
                return item

    def __init__(self, textEdit):
        QtCore.QObject.__init__(self)
        self._textEdit = textEdit
        self._updated.connect(self._write)

    #@QtCore.Slot(basestring)
    def _write(self, text):
        '''
        Appends a text to text edit.
        '''
        if text:
            self._textEdit.insertHtml(text)
            self._textEdit.insertHtml("<br/><br/>")
            self._textEdit.moveCursor(QtGui.QTextCursor.End)

    def _format(self, action, result, device):
        '''
        Formats a result message.
        '''
        d = self._Mapper({"result": result, "device": device},
                         {"result.__class__.__name__": self.RESULT_NAMES})
        if action == "start":
            text = self.START_FORMAT % d
        elif action == "stop":
            text = self.STOP_FORMAT % d
        else:
            return ''
        status = device.status
        if status and status in text:
            text = text.replace(status, "<span style=\"%s\">%s</span>"
                                % (self.STATUS_STYLES[status], status))
        return text

    def start(self, result):
        '''
        Clears the text edit.
        '''
        self._textEdit.clear()

    def startTest(self, result, device):
        '''
        Emits a signal to update the text edit.
        '''
        self._updated.emit(self._format("start", result, device))

    def stopTest(self, result, device):
        '''
        Emits a signal to update the text edit.
        '''
        self._updated.emit(self._format("stop", result, device))


class ConsoleChannel(TestResultChannel):
    '''
    Channel that writes into a text edit widget.
    '''

    def __init__(self, name, console, **params):
        TestResultChannel.__init__(self, name, **params)
        self._console = console

    def start(self, result):
        '''
        Signals start of execution of tests.
        '''
        TestResultChannel.start(self, result)
        if self.isEnabled():
            self._console.start(result)

    def startTest(self, result, device):
        '''
        Signals start of execution of a test.
        '''
        TestResultChannel.startTest(self, result, device)
        if self.isEnabled():
            self._console.startTest(result, device)

    def stopTest(self, result, device):
        '''
        Signals stop of execution of a test.
        '''
        TestResultChannel.stopTest(self, result, device)
        if self.isEnabled():
            self._console.stopTest(result, device)

