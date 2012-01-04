#!/usr/bin/env python

################################################################################
##                                                                            ##
## This file is a part of TADEK.                                              ##
##                                                                            ##
## TADEK - Test Automation in a Distributed Environment                       ##
## (http://tadek.comarch.com)                                                 ##
##                                                                            ##
## Copyright (C) 2011,2012 Comarch S.A.                                       ##
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
from glob import glob
from distutils.core import setup
from distutils.command.install import install as _install
try:
    from tadek.core.config import CONF_DIR, DATA_DIR, VERSION
except ImportError:
    print >> sys.stderr, "Required tadek-common package is not installed"
    exit(1)

DATA_FILES = [
    (os.path.join(DATA_DIR, "ui"),
        glob(os.path.join("src", "*.py"))),
    (os.path.join(DATA_DIR, "ui", "explore"),
        glob(os.path.join("src", "explore", "*.py"))),
    (os.path.join(DATA_DIR, "ui", "test"),
        glob(os.path.join("src", "test", "*.py"))),
    (os.path.join(DATA_DIR, "ui", "result"),
        glob(os.path.join("src", "result", "*.py"))),
    (os.path.join(DATA_DIR, "designer"),
        glob(os.path.join("data", "designer", "*.ui"))),
    (os.path.join(DATA_DIR, "designer", "explore"),
        glob(os.path.join("data", "designer", "explore", "*.ui"))),
    (os.path.join(DATA_DIR, "designer", "test"),
        glob(os.path.join("data", "designer", "test", "*.ui"))),
    (os.path.join(DATA_DIR, "designer", "result"),
        glob(os.path.join("data", "designer", "result", "*.ui"))),
    (os.path.join(CONF_DIR, "tadek-ui"),
        glob(os.path.join("data", "config", "tadek-ui", '*'))),
]

class install(_install):
    sub_commands = []
    # Skip the install_egg_info sub-command
    for name, method in _install.sub_commands:
        if name != "install_egg_info":
            sub_commands.append((name, method))
    del name, method

setup(
    name="tadek-ui",
    version=VERSION,
    description="An advanced TADEK UI client using the PySide library",
    long_description=''.join(['\n', open("README").read()]),
    author="Comarch TADEK Team",
    author_email="tadek@comarch.com",
    license="http://tadek.comarch.com/licensing",
    url="http://tadek.comarch.com/",
    cmdclass={"install": install},
    scripts=["scripts/tadek-ui"],
    data_files=DATA_FILES,
)

