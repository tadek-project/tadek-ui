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
import sys
import unittest
from PySide import QtGui

from tadek.core.config import DATA_DIR
sys.path.insert(0, os.path.join(DATA_DIR, "ui"))
from tadek.engine.testdefs import testStep, TestSuite, TestCase
from tadek.engine.testresult import DeviceExecResult
from result.consolechannel import ConsoleChannel, ConsoleChannelHelper

__all__ = ["ConsoleChannelTest"]

def fakeResult():
    class FakeDevice(object):
        name = "Fake name"
        address =  ("fake address", 0)
        description = "fake description"

    @testStep()
    def step1(test, device, arg1="", arg2=0):
        pass

    @testStep()
    def step2(test, device):
        test.fail()

    @testStep()
    def step3(test, device):
        pass

    class Suite(TestSuite):
        name = "a test suite"
        case1 = TestCase(step1(arg1="abc", arg2=5), step2(), step3())

    device = DeviceExecResult(FakeDevice())
    suite = Suite()
    result = suite.result()
    result.devices.append(device)

    return result, device


class ConsoleChannelTest(unittest.TestCase):
    if not QtGui.qApp:
        _app = QtGui.QApplication([])
    _textEdit = None
    _name = "Console"

    def setUp(self):
        if not self._app:
            self._app = QtGui.QApplication([])
        QtGui.qApp.processEvents()
        self._textEdit = QtGui.QTextEdit()
        self._textEdit.show()
        QtGui.qApp.processEvents()

    def tearDown(self):
        QtGui.qApp.processEvents()
        if self._textEdit:
            self._textEdit.close()
        QtGui.qApp.processEvents()

    def testCreation(self):
        textEdit = QtGui.QTextEdit()
        textEdit.show()

        try:
            h = ConsoleChannelHelper(self._textEdit)
            c = ConsoleChannel(self._name, h)
        except Exception, ex:
            self.fail(ex)

        self.failUnless(c.isEnabled())
        self.failUnlessEqual(self._name, c.name)

    def testStart(self):
        c = ConsoleChannel(self._name, ConsoleChannelHelper(self._textEdit))
        self.failUnless(c.isEnabled())
        self.failIf(self._textEdit.toPlainText())
        c.startTest(*fakeResult())
        self.failUnless(self._textEdit.toPlainText())
        c.start(fakeResult())
        self.failIf(self._textEdit.toPlainText())

    def testStartTest(self):
        c = ConsoleChannel(self._name, ConsoleChannelHelper(self._textEdit))
        self.failIf(self._textEdit.toPlainText())
        c.startTest(*fakeResult())
        self.failUnless(self._textEdit.toPlainText())

    def testStopTest(self):
        c = ConsoleChannel(self._name, ConsoleChannelHelper(self._textEdit))
        self.failIf(self._textEdit.toPlainText())
        c.startTest(*fakeResult())
        self.failUnless(self._textEdit.toPlainText())

    def testEnablingDisabling(self):
        c = ConsoleChannel(self._name, ConsoleChannelHelper(self._textEdit))
        self.failIf(self._textEdit.toPlainText())
        c.startTest(*fakeResult())
        text1 = self._textEdit.toPlainText()
        self.failUnless(text1)
        c._enabled = False
        c.startTest(*fakeResult())
        self.failUnlessEqual(self._textEdit.toPlainText(), text1)
        c._enabled = True
        c.startTest(*fakeResult())
        text2 = self._textEdit.toPlainText()
        self.failUnless(len(text1) < len(text2))

    def testSignalHandling(self):
        message = "test message"
        h = ConsoleChannelHelper(self._textEdit)
        c = ConsoleChannel(self._name, h)
        h._updated.emit(message)
        QtGui.qApp.processEvents()
        self.failUnlessEqual(self._textEdit.toPlainText().strip(), message)

    def testFormatting(self):
        h = ConsoleChannelHelper(self._textEdit)
        h.START_FORMAT = "%(result.id)s"
        c = ConsoleChannel(self._name, h)
        r, d = fakeResult()
        self.failIf(self._textEdit.toPlainText())
        c.startTest(r, d)
        self.failUnlessEqual(self._textEdit.toPlainText().strip(), r.id)


if __name__ == "__main__":
    unittest.main()

