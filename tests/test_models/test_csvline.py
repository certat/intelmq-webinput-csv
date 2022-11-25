import os
import pytest

from pathlib import Path

from intelmq_webinput_csv.lib.csv import CSVLine
from intelmq.lib.utils import load_configuration
from intelmq.lib.message import Event

from ..base import BaseTest

class TestCSVLine(BaseTest):
    
    columns = ['source.ip', 'source.fqdn', 'comment']
    parameters = {
                    'constant_fields': {
                        'classification.taxonomy': 'test'
                    },
                    'custom_rtir_id': '123',
                }

    @pytest.fixture
    def line1(self, request):
        harmonization = super().get_harmonization_config()

        line = CSVLine(
            ['1.1.1.a', 'test@foobar.com', 'foobar'],
            self.columns,
            harmonization=harmonization,
            **self.parameters
        )

        return line

    def test_CSV_creation(self, line1):
        event = line1.parse()

        assert isinstance(event, Event)
        assert len(event) == 5
        assert all(column in event for column in self.columns)