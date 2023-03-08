import pytest

from intelmq_webinput_csv.lib.csv import CSVLine
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
            ['1.1.1.1', 'test@foobar.com', 'foobar'],
            self.columns,
            harmonization=harmonization,
            **self.parameters
        )

        return line

    def test_CSVLine_creation(self, line1):
        event = line1.parse()

        assert isinstance(event, Event)
        assert len(event) == 4
        assert all(column in event for column in self.columns)

    def test_CSVLine_no_columns(self):
        harmonization = super().get_harmonization_config()

        cells = ['1.1.1.1', 'test@foobar.com', 'foobar']

        line = CSVLine(
            cells=cells,
            columns=None,
            harmonization=harmonization,
            **self.parameters
        )

        assert len(line) == 3

        for (column, cell) in line:
            assert column is None
            assert cell in cells
