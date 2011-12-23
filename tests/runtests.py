#!/usr/bin/env python

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
import optparse
import unittest

try:
    import ui
except ImportError:
    srcdir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
    sys.path.insert(0, srcdir)

from tadek.core import config

TEST_MODULES = (
    "consolechannel",
    "devices",
)

_PROGRAM_NAME = 'unittest'
config.setProgramName(_PROGRAM_NAME)

if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.add_option("-v", "--verbosity",
        type="int",
        dest="verbosity",
        default=1,
        help="set the level of verbosity of tests execution to NUM",
        metavar="NUM")
    options, args = parser.parse_args()

    names = []
    for name in (args or TEST_MODULES):
        names.append(name if name.startswith("ut_") else "ut_" + name)
    test = unittest.defaultTestLoader.loadTestsFromNames(names)
    runner = unittest.TextTestRunner(verbosity=options.verbosity)
    result = runner.run(test)

