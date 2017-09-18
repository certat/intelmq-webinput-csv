import os
import sys

sys.path.insert(0, os.path.dirname(__file__) + '/../../')
from intelmq_webinput_csv.bin.backend import app as application
