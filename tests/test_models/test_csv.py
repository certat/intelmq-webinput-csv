import pytest

from intelmq_webinput_csv.lib.csv import CSV

class TestCSV:

    @pytest.fixture
    def file1(self, tmp_path):
        data1 = \
"""column1,column2,column3
line1.1,line1.2,line1.3
line2.1,line2.2,line2.3
line3.1,line3.2,line3.3
"""
        file_path = tmp_path / 'input.csv'

        with open(file_path, 'w+') as f:
            f.write(data1)

        return file_path

    @pytest.fixture
    def parameters(self):
        return {
            'delimiter': ',',
            'quotechar': '"',
            'escapechar': '/',
            'skipInitialSpace': 0,
            'loadLinesMax': 0,
            'has_header': True
        }

    def test_CSV(self, file1, parameters):
        with CSV.create(file1, **parameters) as csv:

            assert csv.num_lines == 3
            assert all(column in csv for column in ['column1', 'column2', 'column3'])