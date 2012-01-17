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

from tadek.core.config import VERSION, getProgramName

import utils

DESCRIPTION = '''%s is an advanced TADEK client using the PySide library.

TADEK is a novel approach to automatic testing and remote control
of applications over accessibility and similar technologies.''' \
    % getProgramName()
COPYRIGHT = '''Copyright &copy; 2011,2012 Comarch S.A.<br>
All rights reserved.'''
WEBSITE_URL = "http://tadek.comarch.com/"
LICENSING_URL = "http://tadek.comarch.com/licensing"


class About(QtCore.QObject):
    '''
    An About dialog class.
    '''
    _ABOUT_UI = "about_dialog.ui"
    _LINK = "<a href=\"%s\">%s</a>"

    def __init__(self):
        QtCore.QObject.__init__(self)
        elements = utils.loadUi(self._ABOUT_UI, parent=utils.window())
        self.dialog = elements["Dialog"]
        elements["buttonClose"].clicked.connect(self.dialog.close)
        elements["labelName"].setText(getProgramName())
        elements["labelVersion"].setText(VERSION)
        elements["labelDescription"].setText(DESCRIPTION)
        elements["labelCopyright"].setText(COPYRIGHT)
        elements["labelWebsite"].setText(self._LINK %
                                         (WEBSITE_URL, WEBSITE_URL))
        elements["labelLicensing"].setText(self._LINK %
                                           (LICENSING_URL, LICENSING_URL))
    def run(self):
        '''
        Shows the dialog and waits until it is closed.
        '''
        self.dialog.exec_()

