import pytest

from pathlib import Path
from flask import current_app as app

from intelmq_webinput_csv.lib import util

from .base import BaseTest


class TestUtil(BaseTest):

    def test_get_temp_file(self):
        before_files = [f for f in self.temp_dir.iterdir() if f.is_file() and f.stem != '.keep']

        util.cleanup_tempdir(age=1_000_000)

        after_files = [f for f in self.temp_dir.iterdir() if f.is_file() and f.stem != '.keep']
        assert len(before_files) == len(after_files)

        util.cleanup_tempdir(age=1)
        after_files = [f for f in self.temp_dir.iterdir() if f.is_file() and f.stem != '.keep']
        assert len(after_files) == 0
