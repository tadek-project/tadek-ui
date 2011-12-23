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

from tadek.engine import testresult
import threading

from tadek.engine.channels import register, TestResultChannel


class ProgressChannelHelper(QtCore.QObject):
    '''
    A helper class to interact with a progress channel.
    It sends signals informing about progress of execution of tests.
    '''
    _PROGRESS_FORMAT = "Ran %%v of %d"
    
    stopped = QtCore.Signal()
    stoppedTest = QtCore.Signal(testresult.TestResultBase,
                                testresult.DeviceExecResult)

    def __init__(self, progressBar):
        QtCore.QObject.__init__(self)
        self._progressBar = progressBar
        self._mutex = threading.RLock()
        self.reset()
        self.stoppedTest.connect(self._update)

    def start(self, result):
        '''
        Prepares the progress bar for next test run.
        '''
        def countCases(res, sum=0):
            if isinstance(res, testresult.TestCaseResult):
                sum += 1
            else:
                for r in res.children:
                    sum += countCases(r)
            return sum

        n = 0        
        for suite in result:
            n += countCases(suite)
        self._mutex.acquire()
        self._toHandle = 0
        self._mutex.release()
        self._stopped = False
        self.reset(n)

    def stopTest(self, result, device):
        '''
        Emits 'stoppedTest' signal and increments the counter of signals
        awaiting to be handled.
        '''
        self._mutex.acquire()
        self._toHandle += 1
        self._mutex.release()
        self.stoppedTest.emit(result, device)


    def stop(self):
        '''
        Emits 'stopped' signal if all previous 'stoppedTest' signals are
        already handled.
        '''
        self._stopped = True
        if self._toHandle == 0:
            self.stopped.emit()

    def reset(self, maximum=None):
        '''
        Resets the progress bar.
        '''
        self._progressBar.reset()
        if maximum is not None:
            self._progressBar.setMaximum(maximum)
            self._progressBar.setValue(0)
            self._progressBar.setFormat(self._PROGRESS_FORMAT % maximum)

    def _update(self, result, device):
        '''
        Updates the progress bar and Emits 'stopped' signal if all previous
        'stoppedTest' signals are already handled.
        '''
        if isinstance(result, testresult.TestCaseResult):
            self._progressBar.setValue(self._progressBar.value() + 1)
        self._mutex.acquire(blocking=0)
        self._toHandle -= 1
        self._mutex.release()
        if self._toHandle == 0 and self._stopped:
            self.stopped.emit()

class ProgressChannel(TestResultChannel):
    '''
    A channel class that sends signals informing about progress in
    a test execution.
    '''
    def __init__(self, name, progress, **params):
        '''
        Initializes the channel and ties it with provided ProgressChannelHelper
        instance.
        '''
        TestResultChannel.__init__(self, name, **params)
        self._progress = progress

    def start(self, result):
        '''
        Signals start of execution of tests.
        '''
        TestResultChannel.start(self, result)
        self._progress.start(result)

    def stopTest(self, result, device):
        '''
        Signals stop of execution of a test.
        '''
        TestResultChannel.stopTest(self, result, device)
        self._progress.stopTest(result, device)

    def stop(self):
        '''
        Signals stop of execution of tests.
        '''
        TestResultChannel.stop(self)
        self._progress.stop()

register(ProgressChannel)

