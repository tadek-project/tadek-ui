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

import datetime

from PySide import QtCore

from tadek.engine.channels import TestResultChannel
from tadek.engine.testresult import (TestResultBase, DeviceExecResult)

class ResultChannelHelper(QtCore.QObject):
    '''
    A helper class to interact with a result channel.
    It maintains a tab in the Result view.
    '''
    _testStarted = QtCore.Signal(TestResultBase, DeviceExecResult)
    _testStopped = QtCore.Signal(TestResultBase, DeviceExecResult)
    _stopped = QtCore.Signal()

    def __init__(self, resultView):
        QtCore.QObject.__init__(self)
        self._resultTab = None
        self._resultView = resultView
        self._testStarted.connect(self._update, QtCore.Qt.QueuedConnection)
        self._testStopped.connect(self._update, QtCore.Qt.QueuedConnection)

    #@QtCore.Slot(TestResultBase, DeviceExecResult)
    def _update(self, result, device):
        '''
        Updates and selects an item associated with given result in the tree
        on the result tab.
        '''
        self._resultTab.update(result)

    def getTab(self):
        '''
        Returns a result tab that is associated with the channel.
        '''
        return self._resultTab

    def start(self, result):
        '''
        Creates a result tab in Result view.
        '''
        self._resultTab = self._resultView.addTab(result,
            str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            select=True, closable=False)
        self._stopped.connect(self._resultTab.expandItems,
                              QtCore.Qt.QueuedConnection)

    def stop(self):
        '''
        Makes the result tab closable
        '''
        self._resultTab.setClosable(True)
        self._stopped.emit()
        self._stopped.disconnect(self._resultTab.expandItems,
                                 QtCore.Qt.QueuedConnection)

    def startTest(self, result, device):
        '''
        Emits a self-connected signal informing about a test being started.
        '''
        self._testStarted.emit(result, device)

    def stopTest(self, result, device):
        '''
        Emits a self-connected signal informing about a test being stopped.
        '''
        self._testStopped.emit(result, device)


class ResultChannel(TestResultChannel):
    '''
    A channel class that maintains a tab in the Result view.
    '''
    def __init__(self, name, result, **params):
        '''
        Initializes the channel and ties it with provided ResultChannelHelper
        instance.
        '''
        TestResultChannel.__init__(self, name, **params)
        self._result = result

    def start(self, result):
        '''
        Signals start of execution of tests.
        '''
        TestResultChannel.start(self, result)
        self._result.start(result)

    def stop(self):
        '''
        Signals stop of execution of tests.
        '''
        TestResultChannel.stop(self)
        self._result.stop()

    def startTest(self, result, device):
        '''
        Signals start of execution of a test.
        '''
        TestResultChannel.startTest(self, result, device)
        self._result.startTest(result, device)

    def stopTest(self, result, device):
        '''
        Signals stop of execution of a test.
        '''
        TestResultChannel.stopTest(self, result, device)
        self._result.stopTest(result, device)

