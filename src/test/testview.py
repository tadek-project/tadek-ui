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
from tadek.core import settings
from tadek.engine import testresult
from tadek.engine import channels
from tadek.engine.runner import TestRunner

import icons
from view import View
from tests import Tests
from devices import Device
from utils import viewName
from dialogs import runWarning, runQuestion
from testdialogs import ReportDialog
from progresschannel import ProgressChannel, ProgressChannelHelper

class TestDeviceList(QtCore.QObject):
    '''
    Manages a device appearance in the view.
    '''
    deviceChecked = QtCore.Signal(Device)
    deviceUnchecked = QtCore.Signal(Device)

    def __init__(self, tree):
        '''
        Initializes the devices view and assigns the reference to TreeWidget
        instance.
        '''
        QtCore.QObject.__init__(self)
        self._tree = tree
        self._tree.itemChanged.connect(self._emitSignals)
        self._dict = {}
        self._warning = False
        self._silent = False

    def _emitSignals(self, item, column):
        '''
        Emits 'deviceChecked' or 'deviceUnchecked' signal based on the state of
        the given item.
        '''
        if self._silent:
            return
        if item is not self._tree.currentItem():
            return
        if item.checkState(0) == QtCore.Qt.Checked:
            self.deviceChecked.emit(self._dict[item.text(0)])
        if item.checkState(0) == QtCore.Qt.Unchecked:
            if (not self.getChecked() and self._warning and
                not runQuestion("Excluding this device will stop execution of "
                                "tests. Are you sure?")):
                self._silent = True
                item.setCheckState(0, QtCore.Qt.Checked)
                QtGui.qApp.processEvents()
                self._silent = False
            else:
                self.deviceUnchecked.emit(self._dict[item.text(0)])

    def add(self, device, check):
        '''
        Adds given device to the list. If check is True, then the new device
        item will be checked.
        '''
        address, port = device.address
        log.debug("Adding '%s' device to view" % device.name)
        item = QtGui.QTreeWidgetItem(self._tree)
        if check:
            item.setCheckState(0, QtCore.Qt.Checked)
        else:
            item.setCheckState(0, QtCore.Qt.Unchecked)
        item.setText(0, device.name)
        item.setText(1, "%s:%d" % (address, port))
        self._tree.resizeColumnToContents(0)
        self._tree.resizeColumnToContents(1)
        self._dict[device.name] = device

    def remove(self, device):
        '''
        Removes given device from the list.
        '''
        if device.name not in self._dict:
            return
        log.debug("Removing device %s from view" % device.name)
        del self._dict[device.name]
        item = self._tree.findItems(device.name, QtCore.Qt.MatchFlags())[0]
        item = self._tree.takeTopLevelItem(self._tree.indexOfTopLevelItem(item))
        if item.checkState(0) == QtCore.Qt.Checked:
            item.setCheckState(0, QtCore.Qt.Unchecked)
        self._tree.resizeColumnToContents(0)
        self._tree.resizeColumnToContents(1)

    def getChecked(self):
        '''
        Returns a list of currently checked devices.
        '''
        devices = []
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            if item.checkState(0) == QtCore.Qt.Checked:
                devices.append(self._dict[item.text(0)])
        return devices

    def setWarning(self, enabled):
        '''
        Enables or disables displaying of a warning before last checked
        device is being unchecked.
        '''
        self._warning = enabled


class Test(View):
    '''
    A view for running test cases.
    '''
    NAME = viewName()
    _UI_FILE = "test_view.ui"
    _ICON_FILE = ":/test/icons/system-run.png"

    _checkOnConnect = settings.get(NAME, "options", "check_on_connect",
                                   default="Yes", force=True)

    # Menus and Tool bar
    _menuFile = (
        "actionAdd",
        "actionRemove",
        None
    )
    _menuEdit = (
        "actionExpand",
        "actionExpandAll",
        "actionCollapse",
        "actionCollapseAll",
        None
    )
    _menuView = (
        "actionRefresh",
        None
    )
    _toolBar = (
        "actionAdd",
        "actionRemove",
        None,
        (
            "actionExpand",
            "actionExpandAll"
        ),
        (
            "actionCollapse",
            "actionCollapseAll"
        ),
        "actionRefresh",
        None,
        "actionStart",
        "actionPause",
        "actionResume",
        "actionStop"
    )

    def __init__(self, parent):
        View.__init__(self, parent)
        self._devices = TestDeviceList(self._elements["treeWidgetDevices"])

        self._actionStart = self._elements["actionStart"]
        self._actionStop = self._elements["actionStop"]
        self._actionPause = self._elements["actionPause"]
        self._actionResume = self._elements["actionResume"]

        self._actionStart.triggered.connect(self._startTests)
        self._actionStop.triggered.connect(self._stopTests)
        self._actionPause.triggered.connect(self._pauseTests)
        self._actionResume.triggered.connect(self._resumeTests)

        self._actionStart.setVisible(True)
        self._actionStop.setVisible(False)
        self._actionPause.setVisible(False)
        self._actionResume.setVisible(False)

        # Summary channel
        channels.add("SummaryChannel", "_ui_summary")

        # Progress channel
        pBar = QtGui.QProgressBar()
        pBar.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        font = pBar.font()
        font.setBold(True)
        pBar.setFont(font)
        self._parent.getStatusBar().addPermanentWidget(pBar, 1)
        self._progress = ProgressChannelHelper(pBar)
        channels.add(ProgressChannel, "_ui_progress", progress=self._progress)
        self._progress.testStarted.connect(self._onTestStarted)
        self._progress.testStopped.connect(self._onTestStopped)
        self._progress.stopped.connect(self._onStopped)

        self._tests = Tests(self._elements["treeWidgetLocations"],
                            self._elements["treeWidgetTests"],
                            self._elements["treeWidgetModels"])

        self._elements["actionAdd"].triggered.connect(self._tests.addLocation)
        self._elements["actionRemove"].triggered.connect(
                                                     self._tests.removeLocation)
        self._elements["actionExpand"].triggered.connect(
                                                     self._tests.expandSelected)
        self._elements["actionExpandAll"].triggered.connect(
                                                          self._tests.expandAll)
        self._elements["actionCollapse"].triggered.connect(
                                                   self._tests.collapseSelected)
        self._elements["actionCollapseAll"].triggered.connect(
                                                        self._tests.collapseAll)
        self._elements["actionRefresh"].triggered.connect(self._tests.refresh)

        # Initialize private test variables
        self._suiteRuns = 0
        self._todoSuites = 0
        self._testResult = None
        self._testRunner = None

# Public methods:
    def saveState(self):
        '''
        Saves the view's state to configuration.
        '''
        View.saveState(self)
        self._tests.saveState()

    def loadState(self):
        '''
        Loads the view's state from configuration.
        '''
        View.loadState(self)
        self._tests.loadState()

# Slots:
    #@QtCore.Slot(Device)
    def _deviceConnected(self, device):
        '''
        Adds a device to list.
        '''
        self._devices.add(device, check=self._checkOnConnect.getBool())

    #@QtCore.Slot(Device)
    def _deviceDisconnected(self, device, error):
        '''
        Removes given device from list. The error parameter can be set to True
        to indicate that the device was disconnected due to an error.
        '''
        self._devices.remove(device)

    #@QtCore.Slot()
    def _startTests(self):
        '''
        Starts execution of tests.
        '''
        log.debug("Starting tests")
        self._actionStart.setVisible(False)
        devices = self._devices.getChecked()
        if not devices:
            runWarning("Select some devices first")
            self._actionStart.setVisible(True)
            return
        tests = self._tests.getCheckedTests()
        if not tests:
            self._actionStart.setVisible(True)
            return
        if sum([test.count() for test in tests]) == 0:
            runWarning("Selected test suites do not contain any test cases")
            self._actionStart.setVisible(True)
            return

        self._suiteRuns = 0
        self._todoSuites = len(tests)
        self._testResult = testresult.TestResult()
        self._testRunner = TestRunner(devices, tests, self._testResult)
        self._devices.deviceChecked.connect(self._testRunner.addDevice)
        self._devices.deviceUnchecked.connect(self._testRunner.removeDevice)
        self._devices.setWarning(True)

        self._testRunner.start()

        self._actionStop.setVisible(True)
        self._actionPause.setVisible(True)

    #@QtCore.Slot()
    def _stopTests(self):
        '''
        Stops execution of tests.
        '''
        log.debug("Stopping tests")
        self._actionStart.setVisible(True)
        self._actionStop.setVisible(False)
        self._actionPause.setVisible(False)
        self._actionResume.setVisible(False)
        self._testRunner.stop()

    #@QtCore.Slot()
    def _pauseTests(self):
        '''
        Pauses execution of tests.
        '''
        log.debug("Pausing tests")
        self._actionStart.setVisible(False)
        self._actionStop.setVisible(True)
        self._actionPause.setVisible(False)
        self._actionResume.setVisible(True)
        self._testRunner.pause()

    #@QtCore.Slot()
    def _resumeTests(self):
        '''
        Resumes execution of tests.
        '''
        log.debug("Resuming tests")
        self._actionStart.setVisible(False)
        self._actionStop.setVisible(True)
        self._actionPause.setVisible(True)
        self._actionResume.setVisible(False)
        self._testRunner.resume()

    #@QtCore.Slot(testresult.TestResultBase, testresult.DeviceExecResult)
    def _onTestStarted(self, result, device):
        '''
        Handles a start test execution of a test represented by the given
        result.
        '''
        if isinstance(result, testresult.TestCaseResult):
            log.debug("Began execution of test case: %s" % result.id)
        # If it is a top-level test suite result then increase the counter of
        # running top-level test suites
        if result.parent is None:
            self._suiteRuns += 1

    #@QtCore.Slot(testresult.TestResultBase, testresult.DeviceExecResult)
    def _onTestStopped(self, result, device):
        '''
        Handles a stop test execution of a test represented by the given
        result.
        '''
        if isinstance(result, testresult.TestCaseResult):
            log.debug("Finished execution of test case: %s" % result.id)
        # If it is a top-level test suite result then decrease the counters of
        # running top-level test suites and to do test suites.
        if result.parent is None:
            self._suiteRuns -= 1
            self._todoSuites -= 1
            # If all top-level test suites are done then join() the test runner
            if self._suiteRuns == 0 and self._todoSuites <= 0:
                self._testRunner.join()

    #@QtCore.Slot()
    def _onStopped(self):
        '''
        Shows summary dialog after finishing test executions.
        '''
        log.debug("All tests finished")

        self._actionStart.setVisible(True)
        self._actionStop.setVisible(False)
        self._actionPause.setVisible(False)
        self._actionResume.setVisible(False)

        self._devices.deviceChecked.disconnect(self._testRunner.addDevice)
        self._devices.deviceUnchecked.disconnect(self._testRunner.removeDevice)
        self._devices.setWarning(False)

        files = []
        for c in self._testRunner.result.get():
            if isinstance(c, channels.TestResultFileChannel) and c.isActive():
                files.append((c.name, c.filePath()))
        dialog = ReportDialog(
                        self._testResult.get(name='_ui_summary')[0].getSummary(),
                        files, len(self._devices.getChecked()) > 0)
        dialog.closed.connect(self._progress.reset,
                              type=QtCore.Qt.DirectConnection)
        dialog.runAgainClicked.connect(self._startTests,
                                       type=QtCore.Qt.QueuedConnection)
        dialog.showDetailsClicked.connect(self._showDetails)
        dialog.run()

    #@QtCore.Slot()
    def _showDetails(self):
        '''
        Shows execution result in Result view.
        '''
        resultView = self._parent.getView("result")
        if resultView is not None:
            log.debug("Showing details in Result view")
            resultView.activate()
            resultView.showLastResult()

