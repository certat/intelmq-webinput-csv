import pytest

from intelmq_webinput_csv.lib.csv import CSVLine
from intelmq_webinput_csv.lib.exceptions import InvalidCSVLine
from intelmq.lib.exceptions import InvalidValue, InvalidKey, KeyExists, KeyNotExists

from ..base import BaseTest


class TestExceptions(BaseTest):

    @pytest.fixture
    def invalid_value(self):
        return InvalidValue("source.ip", "foobar")

    @pytest.fixture
    def csv_line(self):
        columns = ['source.ip', 'source.fqdn', 'comment']
        harmonization = super().get_harmonization_config()

        line = CSVLine(
            ['foobar', 'test@foobar.com', 'foobar'],
            columns,
            index=10,
            harmonization=harmonization
        )

        return line

    def test_invalid_csv_line_exception_in_invalid_value(self, invalid_value, csv_line):
        exception = InvalidCSVLine(invalid_value, csv_line)

        assert exception.key == 'source.ip'
        assert exception.value == 'foobar'
        assert exception.line_index == 10
        assert exception.column_index == 0

        message = exception.message
        assert str(invalid_value) in message
        assert '10' in message

    def test_invalid_csv_line_exception_in_invalid_key(self, csv_line):
        key = 'source.fqdn'

        for except_type in [InvalidKey, KeyExists, KeyNotExists]:
            invalid_value = except_type(key)
            exception = InvalidCSVLine(invalid_value, csv_line)

            assert exception.key == key
            assert not hasattr(exception, 'value')
            assert not hasattr(exception, 'type')
            assert exception.line_index == 10
            assert exception.column_index == 1

            message = exception.message
            assert str(invalid_value) in message
            assert '10' in message
