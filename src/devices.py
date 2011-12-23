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

from PySide import QtCore, QtGui

import dialogs
import utils
from tadek.core import log
from tadek.core import queue
from tadek.core import devices
from tadek.connection import client
from tadek.connection import device
from tadek.connection import protocol
from tadek.connection import ConnectionError


class Queue(QtCore.QObject, queue.Queue):
    '''
    Creates a queue object that uses Qt signals.
    '''
    # Signals:
    notEmpty = QtCore.Signal(int)
    allDone = QtCore.Signal(int)

    def __init__(self):
        '''
        Initializer.
        '''
        QtCore.QObject.__init__(self)
        queue.Queue.__init__(self)

    def _notifyNotEmpty(self, id):
        '''
        Notifies the queue is not empty.
        '''
        queue.Queue._notifyNotEmpty(self, id)
        self.notEmpty.emit(id)

    def _notifyAllDone(self, id):
        '''
        Notifies all tasks of the given id are done in queue.
        '''
        queue.Queue._notifyAllDone(self, id)
        if id is None:
            id = -1
        self.allDone.emit(id)


class DeviceObject(QtCore.QObject):
    '''
    An interface class of devices that emit various signals.
    '''
    # Signals:
    connected =  QtCore.Signal()
    disconnected = QtCore.Signal()
    requestSent = QtCore.Signal(int)
    responseReceived = QtCore.Signal(int)
    errorOccurred = QtCore.Signal()

    # Device methods:
    _connectDevice = None
    _disconnectDevice = None

    def __init__(self):
        QtCore.QObject.__init__(self)
        if not hasattr(self, "client"):
            raise NotImplementedError
        self.client.messages.notEmpty.connect(self._responseReceived,
                                              type=QtCore.Qt.QueuedConnection)
        self._connected = False

    def connectDevice(self, *args, **kwargs):
        '''
        Connects the device and emits the 'connected' signal.
        '''
        if self._connectDevice(*args, **kwargs):
            self._connected = True
            self.connected.emit()

    def disconnectDevice(self, *args, **kwargs):
        '''
        Disconnects the device and emits the 'disconnected' signal.
        '''
        if self._disconnectDevice(*args, **kwargs) or self._connected:
            self._connected = False
            self.disconnected.emit()

    def requestDevice(self, reqfunc, *args, **kwargs):
        '''
        Sends a request using the given function and emits the 'requestSent'
        signal.
        '''
        try:
            id = getattr(self, reqfunc)(*args, **kwargs)
        except Exception, err:
            if not isinstance(err, ConnectionError):
                err = client.Error(err)
            log.exception(err)
        else:
            self.requestSent.emit(id)
            return id

    #@QtCore.Slot(int)
    def _responseReceived(self, id):
        '''
        Emits 'responseReceived' or 'errorOccurred' signal.
        '''
        log.debug("Received message from '%s' device: %d" % (self.name, id))
        if id > protocol.DEFAULT_MSG_ID:
            self.responseReceived.emit(id)
        elif id == protocol.ERROR_MSG_ID:
            if self._connected:
                self.errorOccurred.emit()
            else:
                log.warning("Ignore error received from '%s' device: %s"
                             % (self.name, self.client.error()))


class Client(client.Client):
    '''
    A client class using UI queue.
    '''
    queueClass = Queue


class Device(DeviceObject, device.Device):
    '''
    A class of devices that emit various signals.
    '''
    clientClass = Client

    _connectDevice = device.Device.connect
    _disconnectDevice = device.Device.disconnect

    def __init__(self, *args, **kwargs):
        device.Device.__init__(self, *args, **kwargs)
        DeviceObject.__init__(self)


class XmlClient(client.XmlClient):
    '''
    An XML client class using UI queue.
    '''
    queueClass = Queue


class OfflineDevice(DeviceObject, device.OfflineDevice):
    '''
    A class of devices that emit various signals.
    '''
    clientClass = XmlClient

    _connectDevice = device.OfflineDevice.connect
    _disconnectDevice = device.OfflineDevice.disconnect

    def __init__(self, *args, **kwargs):
        device.OfflineDevice.__init__(self, *args, **kwargs)
        DeviceObject.__init__(self)


class DeviceItem(QtGui.QTreeWidgetItem, QtCore.QObject):
    '''
    Class of device tree items.
    '''

    _ITEM_BUTTON_STYLE = "text-align: center; margin-left: 0; padding: 2 5 2 5"
    _ITEM_CHECKED_BUTTON_NAME = "Disconnect"
    _ITEM_UNCHECKED_BUTTON_NAME = "Connect"
    _ITEM_CHECKED_BUTTON_ICON = ":/icons/user-online.png"
    _ITEM_UNCHECKED_BUTTON_ICON = ":/icons/user-offline.png"

    buttonToggled = QtCore.Signal(bool, Device)

    def __init__(self, tree, dev):
        '''
        Initializes a device item and binds it to device signals.
        
        :param tree: A parent tree
        :type tree: QtGui.QTreeWidget
        :param dev: A device
        :type dev: Device
        '''
        QtCore.QObject.__init__(self)
        QtGui.QTreeWidgetItem.__init__(self, tree,
                                       (dev.name, "%s:%d" % dev.address, ''))
        self._tree = tree
        for icon in ("_ITEM_CHECKED_BUTTON_ICON",
                     "_ITEM_UNCHECKED_BUTTON_ICON"):
            setattr(self, icon, QtGui.QIcon(getattr(self, icon)))
        widget = QtGui.QWidget(tree)
        tree.setItemWidget(self, 2, widget)
        button = QtGui.QPushButton(self._ITEM_UNCHECKED_BUTTON_ICON,
                                   self._ITEM_UNCHECKED_BUTTON_NAME, widget)
        button.setIconSize(QtCore.QSize(11, 11))
        button.setStyleSheet(self._ITEM_BUTTON_STYLE)
        button.setCheckable(True)
        layout = QtGui.QHBoxLayout()
        layout.setContentsMargins(1, 1, 1, 1)
        layout.addWidget(button)
        widget.setLayout(layout)
        widget.setFixedHeight(button.height())
        widget.setFixedWidth(button.width() + 15)
        self._button = button
        QtGui.qApp.processEvents()
        self._device = dev
        self._device.connected.connect(self._updateButton)
        self._device.disconnected.connect(self._updateButton)
        self._button.clicked.connect(self._buttonClicked)
        self.updateDevice()

# Public methods:
    def updateDevice(self):
        '''
        Updates the displayed name and address of the device.
        '''
        log.debug("Updating dev item: %s" % self._device)
        self.setText(0, self._device.name)
        self.setText(1, "%s:%d" % self._device.address)
        self._updateButton()

# Slots:
    #QtCore.Slot()
    def _buttonClicked(self):
        '''
        Emits the 'buttonToggled' signal.
        '''
        self._button.setChecked(False)
        self.buttonToggled.emit(self._button.text() ==
                                self._ITEM_UNCHECKED_BUTTON_NAME,
                                self._device)

    #QtCore.Slot()
    def _updateButton(self):
        '''
        Sets checked state, icon and text of a button corresponding to
        connection state of the device.
        '''
        connected = self._device.isConnected()
        self._button.setChecked(connected)
        self._button.setIcon(self._ITEM_CHECKED_BUTTON_ICON if connected
                                else self._ITEM_UNCHECKED_BUTTON_ICON)
        self._button.setText(self._ITEM_CHECKED_BUTTON_NAME if connected
                                else self._ITEM_UNCHECKED_BUTTON_NAME)

        
class DevicesDialog(QtCore.QObject):
    '''
    A manage devices dialog class.
    '''
    _DIALOG_UI = "devices_dialog.ui"
    _N_COLS = 3

# Signals:
    connected =  QtCore.Signal(device.Device)
    disconnected = QtCore.Signal(device.Device, bool)
    requestSent = QtCore.Signal(device.Device, int)
    responseReceived = QtCore.Signal(device.Device, int)

    def __init__(self):
        QtCore.QObject.__init__(self)
        elements = utils.loadUi(self._DIALOG_UI, parent=utils.window())
        self.dialog = elements["Dialog"]
        self._deviceList = elements["treeWidgetDevices"]
        elements["buttonClose"].clicked.connect(self.dialog.close)
        self._deviceList.itemSelectionChanged.connect(self._updateDialogButtons)
        elements["buttonConnectAll"].clicked.connect(self._connectAll)
        elements["buttonDisconnectAll"].clicked.connect(self._disconnectAll)
        self._addButton = elements["buttonAdd"]
        self._addButton.clicked.connect(self._addDevice)
        self._editButton = elements["buttonEdit"]
        self._editButton.clicked.connect(self._editDevice)
        self._removeButton = elements["buttonRemove"]
        self._removeButton.clicked.connect(self._removeDevice)
        self._deviceItems = {}
        self._errors = {}
        self._refresh()

# Public methods:
    def unload(self):
        '''
        Disconnect and unload all current devices from the dialog.
        '''
        log.debug("Unloading device list")
        for dev in devices.all():
            self._updateConnectionState(False, dev)

    def firstRun(self):
        '''
        Runs devices dialog if no devices are connected, and additionally runs
        the Add device dialog if there are no devices defined.
        '''
        log.debug("First running manage devices dialog")
        empty = True
        connected = False
        for dev in self._deviceItems:
            empty = False
            if bool(dev.params.get("autoconnect", False)):
                self._updateConnectionState(True, dev)
            if not connected and dev.isConnected():
                connected = True
        if not connected:
            self.dialog.show()
        if empty:
            self._addDevice()

    def run(self):
        '''
        Runs the manage devices dialog.
        '''
        log.debug("Running manage devices dialog")
        self._refresh()
        self.dialog.show()

# Private methods:
    def _addDeviceItem(self, dev):
        '''
        Adds an item for given device. 

        :param dev: A device
        :type dev: Device
        '''
        item = DeviceItem(self._deviceList, dev)
        item.buttonToggled.connect(self._updateConnectionState)
        self._deviceItems[dev] = item
        # Fix column sizes
        for col in xrange(self._N_COLS):
            self._deviceList.resizeColumnToContents(col)
        dev.connected.connect(self._deviceConnected)
        dev.disconnected.connect(self._deviceDisconnected)
        dev.requestSent.connect(self._requestSent)
        dev.responseReceived.connect(self._responseReceived)
        dev.errorOccurred.connect(self._errorOccurred)

    def _removeDeviceItem(self, dev):
        '''
        Removes an item corresponding to given device.

        :param dev: A device
        :type dev: Device
        '''
        log.debug("Removing dev item: %s" % dev)
        index = self._deviceList.indexOfTopLevelItem(self._deviceItems[dev])
        self._deviceList.takeTopLevelItem(index)
        for col in xrange(self._N_COLS):
            self._deviceList.resizeColumnToContents(col)
        self._deviceItems.pop(dev)

    def _refresh(self):
        '''
        Refreshes the list of devices.
        '''
        log.debug("Refreshing device list")
        devices.load(type=Device)
        for dev in self._deviceItems.keys()[:]:
            if devices.get(dev.name) is None and not dev.isConnected():
                self._removeDeviceItem(dev)
        for dev in devices.all():
            if dev not in self._deviceItems:
                self._addDeviceItem(dev)
        self._updateDialogButtons()

# Slots:
    #@QtCore.Slot()
    def _addDevice(self):
        '''
        Runs the 'Add device' dialog.
        '''
        log.debug("Adding new device")
        dialog = DeviceConfigDialog()
        if not dialog.run():
            return
        connect = dialog.params.pop("connect", False)
        dev = devices.add(type=Device, **dialog.params)
        self._addDeviceItem(dev)
        log.info("New device added: %s" % dev)
        if connect:
            self._updateConnectionState(True, dev)

    #@QtCore.Slot()
    def _editDevice(self):
        '''
        Runs the 'Edit device' dialog for currently selected device.
        '''
        items = self._deviceList.selectedItems()
        if not items:
            return
        dev = devices.get(items[0].text(0))
        log.debug("Editing device: %s" % dev)
        dialog = DeviceConfigDialog(dev)
        if not dialog.run():
            return
        connect = dialog.params.pop("connect", False)
        if dev.name != dialog.params["name"]:
            self._updateConnectionState(False, dev)
            devices.remove(dev.name)
            index = self._deviceList.indexOfTopLevelItem(items[0])
            self._deviceList.takeTopLevelItem(index)
            dev = devices.add(type=Device, **dialog.params)
            self._addDeviceItem(dev)
        else:
            address = dialog.params["address"]
            port = dialog.params["port"]
            if dev.address != (address, port):
                self._updateConnectionState(False, dev)
            devices.update(**dialog.params)
            self._deviceItems[dev].updateDevice()
        log.info("Device edited: %s" % dev)
        if connect:
            self._updateConnectionState(True, dev)

    #@QtCore.Slot()
    def _removeDevice(self):
        '''
        Removes the currently selected device.
        '''
        items = self._deviceList.selectedItems()
        if not items:
            return
        dev = devices.get(items[0].text(0))
        if not dialogs.runQuestion("Do you want to remove "
                                   "'%s' device permanently?" % dev.name):
            return
        log.debug("Removing device: %s" % dev)
        self._updateConnectionState(False, dev)
        devices.remove(dev.name)
        self._removeDeviceItem(dev)
        log.info("Device removed: %s" % dev)

    #@QtCore.Slot()
    def _deviceConnected(self):
        '''
        Emits the 'connected' device signal.
        '''
        dev = self.sender()
        log.info("Device connected: %s" % dev)
        self.connected.emit(dev)

    #@QtCore.Slot()
    def _deviceDisconnected(self):
        '''
        Emits the 'disconnected' device signal.
        '''
        dev = self.sender()
        log.info("Device disconnected: %s" % dev)
        self.disconnected.emit(dev, self._errors.pop(dev, None) is not None)

    #@QtCore.Slot(int)
    def _requestSent(self, id):
        '''
        Emits the 'requestSent' device signal.

        :param id: Id of sent request
        :type id: int
        '''
        dev = self.sender()
        log.debug("Device request sent: %s" % dev)
        self.requestSent.emit(dev, id)

    #@QtCore.Slot(int)
    def _responseReceived(self, id):
        '''
        Emits the 'responseReceived' device signal.

        :param id: Id of received response
        :type id: int
        '''
        dev = self.sender()
        log.debug("Device response received: %s" % dev)
        self.responseReceived.emit(dev, id)

    #@QtCore.Slot()
    def _errorOccurred(self):
        '''
        Disconnects a device in case of a ConnectionLostError.
        '''
        dev = self.sender()
        err = dev.getError()
        log.error("Error occurred in '%s' device: %s" % (dev.name, err))
        if isinstance(err, client.ConnectionLostError):
            try:
                dialogs.runError("'%s' device disconnected:\n%s"
                                 % (dev.name, err))
                self._errors[dev] = err
                self._updateConnectionState(False, dev)
            except ConnectionError, ex:
                log.error("Connection Error (%s): %s" % (dev, ex))

    #@QtCore.Slot()
    def _updateConnectionState(self, state, dev):
        '''
        Connects or disconnects a device.

        :param state: Desired connection state
        :type state: boolean
        :param dev: A device
        :type dev: Device
        '''
        log.debug("%s '%s' device"
                  % ("Connecting" if state else "Disconnecting", dev))
        try:
            if state:
                dev.connectDevice()
            else:
                dev.disconnectDevice()
        except ConnectionError, err:
            dialogs.runError("Error occurred in connection to '%s' device:\n%s"
                              % (dev.name, str(err)))

    #@QtCore.Slot()
    def _connectAll(self):
        '''
        Connects all devices.
        '''
        log.debug("Connecting all devices")
        for dev in devices.all():
            self._updateConnectionState(True, dev)

    #@QtCore.Slot()
    def _disconnectAll(self):
        '''
        Disconnects all devices.
        '''
        log.debug("Disconnecting all devices")
        for dev in devices.all():
            self._updateConnectionState(False, dev)

    #@QtCore.Slot()
    def _updateDialogButtons(self):
        '''
        Updates state of Edit and Remove buttons.
        '''
        state = bool(self._deviceList.selectedItems())
        log.debug("%s devices dialog buttons"
                  % ("Enabling" if state else "Disabling"))
        self._editButton.setEnabled(state)
        self._removeButton.setEnabled(state)


class DeviceConfigDialog(QtCore.QObject):
    '''
    A device configuration dialog class.
    '''
    _DIALOG_UI = "deviceconfig_dialog.ui"
    _CONFIG_NAME = "devicesdialog"
    _CONFIG_SECTION_COMPLETERS = "completers"

    def __init__(self, dev=None):
        '''
        Initializer.

        :param dev: A device to configure. If not provided, a new device
            will be added
        :type dev: Device
        '''
        QtCore.QObject.__init__(self)
        elements = utils.loadUi(self._DIALOG_UI, parent=utils.window())
        self.dialog = elements["Dialog"]
        self.dialog.setWindowTitle("Edit device" if dev else "Add device")
        elements["buttonBox"].accepted.connect(self._accept)
        self._name = elements["lineEditName"]
        self._desc = elements["lineEditDescription"]
        self._address = elements["comboBoxAddress"]
        self._address.completer().setCaseSensitivity(QtCore.Qt.CaseSensitive)
        self._lastAddresses = utils.LastValues(self._CONFIG_NAME,
                                               self._CONFIG_SECTION_COMPLETERS,
                                               "address")
        self._lastAddresses.add(devices.DEFAULT_IP)
        self._port = elements["spinBoxPort"]
        self._port.setValue(devices.DEFAULT_PORT)
        self._connect = elements["checkBoxConnect"]
        self._connect.setChecked(True)
        self._autoconnect = elements["checkBoxAutoconnect"]
        self._device = dev
        if dev:
            self._name.setText(dev.name)
            self._desc.setText(dev.description)
            address, port = dev.address
            self._lastAddresses.add(address)
            self._port.setValue(port)
            autoconnect = dev.params.get("autoconnect", False)
            self._autoconnect.setChecked(bool(autoconnect))
        for addr in self._lastAddresses.all():
            self._address.addItem(addr)
        self._address.setCurrentIndex(0)
        # New created device
        self.params = None

# Slots:
    #@QtCore.Slot()
    def _accept(self):
        '''
        Accepts provided device data.
        '''
        log.debug("Accepting device data")
        # Test provided name
        name = self._name.text()
        if not name:
            dialogs.runError("'name' field is required")
            return
        # Test provided address
        address = self._address.currentText()
        if not address:
            dialogs.runError("'address' field is required")
            return
        if ((not self._device or self._device.name != name)
            and devices.get(name) is not None):
            dialogs.runError("'%s' name already in use" % name)
            return
        self.params = {
            "name": name,
            "description": self._desc.text() or '',
            "address": address,
            "port": self._port.value(),
            "connect": self._connect.isChecked(),
            "autoconnect": self._autoconnect.isChecked()
        }
        self._lastAddresses.add(address)
        self.dialog.accept()

    #@QtCore.Slot()
    def run(self):
        '''
        Runs the edit device dialog.
        '''
        log.debug("Running device configuration dialog")
        return self.dialog.exec_() == self.dialog.Accepted

