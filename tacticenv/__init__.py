###########################################################
#
# Copyright (c) 2005, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
#
#

__all__ = ['get_install_dir', 'get_site_dir', 'get_data_dir', 'get_temp_dir']

import os, sys

install_dir = None
site_dir = None
data_dir = None

def get_install_dir():
    return install_dir

def get_site_dir():
    return site_dir

def get_data_dir():
    return data_dir

def get_temp_dir():
    from pyasm.common import Environment 
    temp_dir = Environment.get_tmp_dir()

    return temp_dir

# Defualt Tactic Installations
from .tactic_paths import *

# give a chance for the user to override Tactic location
if 'TACTIC_INSTALL_DIR' not in os.environ:
    # set some paths
    install_dir = TACTIC_INSTALL_DIR
    os.environ['TACTIC_INSTALL_DIR'] = install_dir
else:
    # get it from the environment
    install_dir = os.environ["TACTIC_INSTALL_DIR"]

if 'TACTIC_SITE_DIR' not in os.environ:
    site_dir = TACTIC_SITE_DIR
    os.environ['TACTIC_SITE_DIR'] = site_dir
else:
    site_dir = os.environ["TACTIC_SITE_DIR"]

if 'TACTIC_DATA_DIR' not in os.environ:
    data_dir = TACTIC_DATA_DIR
    os.environ['TACTIC_DATA_DIR'] = data_dir
else:
    data_dir = os.environ["TACTIC_DATA_DIR"]



# give a chance for the user to override Tactic config path
if site_dir and 'TACTIC_CONFIG_PATH' not in os.environ:
    if os.name == 'nt':
        osname = "win32"
    else:
        osname = "linux"

    os.environ['TACTIC_CONFIG_PATH'] = "%s/config/tactic_%s-conf.xml" \
            % (site_dir, osname)


install_dir = install_dir.replace("\\", "/")

# add it to the paths
sys.path.insert(0, "%s/src" % install_dir)
sys.path.insert(0, install_dir)

# add the api libraries
sys.path.insert(0, "%s/src/client" % install_dir)



