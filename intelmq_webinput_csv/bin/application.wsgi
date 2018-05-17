# Copyright (c) 2017-2018 nic.at GmbH <wagner@cert.at>
# SPDX-License-Identifier: AGPL-3.0
import os
import sys

sys.path.insert(0, os.path.dirname(__file__) + '/../../')
from intelmq_webinput_csv.bin.backend import app as application
