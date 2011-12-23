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
import time
import socket
import unittest
from PySide import QtCore, QtGui

from devices import Device, Queue
from tadek.core import config
sys.path.insert(0, os.path.join(config.DATA_DIR, "ui"))
from tadek.core.queue import QueueItem
from tadek.connection import protocol, server

__all__ = ["QueueTest", "DeviceTest"]


class QueueWatcher(QtCore.QObject):
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.queue = Queue()
        self.queue.notEmpty.connect(self.notEmpty)
        self.queue.allDone.connect(self.allDone)
        self.empty = True
        self.done = False

    #@QtCore.Slot(int)
    def notEmpty(self, id):
        self.empty = False

    #@QtCore.Slot(int)
    def allDone(self, id):
        self.done = True


class QueueTest(unittest.TestCase):
    def testNotEmpty(self):
        qw = QueueWatcher()
        qw.queue.put(QueueItem(1))
        self.failIf(qw.empty)

    def testAllIdDone(self):
        qw = QueueWatcher()
        self.failUnless(qw.empty)
        qw.queue.done(1)
        self.failUnless(qw.done)

    def testAllDone(self):
        qw = QueueWatcher()
        self.failUnless(qw.empty)
        qw.queue.done()
        self.failUnless(qw.done)


class DeviceDaemon(server.Server):
    _info = protocol.create(protocol.MSG_TYPE_RESPONSE,
                            protocol.MSG_TARGET_SYSTEM,
                            protocol.MSG_NAME_INFO,
                            version=config.VERSION,
                            locale='', extensions=(),  status=True).marshal()

    def handle_accept(self):
        handler = server.Server.handle_accept(self)
        handler.push(''.join([self._info, handler.get_terminator()]))


class DeviceWatcher(QtCore.QObject):
    def __init__(self, device):
        QtCore.QObject.__init__(self)
        self.device = device
        self.connected = device.isConnected()
        self.sent = False
        self.received = False
        device.connected.connect(self._connected)
        device.disconnected.connect(self._disconnected)
        device.requestSent.connect(self._requestSent)
        device.responseReceived.connect(self._responseReceived)

    #@QtCore.Slot()
    def _connected(self):
        self.connected = True

    #@QtCore.Slot()
    def _disconnected(self):
        self.connected = False

    #@QtCore.Slot(int)
    def _requestSent(self, id):
        self.sent = True

    #@QtCore.Slot(int)
    def _responseReceived(self, id):
        self.received = True


class DeviceTest(unittest.TestCase):
    if not QtGui.qApp:
        _app = QtGui.QApplication([])
    NAME = "TestDevice"
    ADDRESS = "127.0.0.1"
    PORT = 2**14
    _port = PORT
    _sock = None
    _dev = None

    def setUp(self):
        QtGui.qApp.processEvents()
        self.__class__._port += 1
        self._daemon = DeviceDaemon((self.ADDRESS, self._port))
        self._dev = Device(self.NAME, self.ADDRESS, self._port)
        QtGui.qApp.processEvents()

    def tearDown(self):
        QtGui.qApp.processEvents()
        self._dev.disconnectDevice()
        self._daemon.close()
        QtGui.qApp.processEvents()

    def testDeviceList(self):
        '''
        Tests creation of a list of 3 devices. There is an issue about it.
        '''
        def createDevice(name):
            return Device(name, self.ADDRESS, self.PORT)
        N_DEVS = 3
        devs = [createDevice(self.NAME + str(i)) for i in xrange(N_DEVS)]
        self.failUnlessEqual(len(devs), N_DEVS)

    def testConnecting(self):
        '''
        Tries to create three devices.
        '''
        dw = DeviceWatcher(self._dev)
        self._dev.connectDevice()
        self.failUnless(dw.connected)

    def testDisconnecting(self):
        dw = DeviceWatcher(self._dev)
        self._dev.connectDevice()
        self.failUnless(dw.connected)
        self._dev.disconnectDevice()
        self.failIf(dw.connected)

    def testSendingReqest(self):
        dw = DeviceWatcher(self._dev)
        self._dev.connectDevice()
        self.failUnless(dw.connected)
        self._dev.requestDevice("requestSystemExec", "ls -l")
        self.failUnless(dw.sent)

    def testReceivingResponse(self):
        dw = DeviceWatcher(self._dev)
        self._dev.connectDevice()
        self.failUnless(dw.connected)
        self._dev.client.messages.put(QueueItem(1))
        QtGui.qApp.processEvents()
        self.failUnless(dw.received)


if __name__ == "__main__":
    unittest.main()

