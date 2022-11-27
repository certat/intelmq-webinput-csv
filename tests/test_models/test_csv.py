import pytest

from intelmq_webinput_csv.lib.csv import CSV

from ..base import BaseTest


class TestCSV(BaseTest):

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
            'has_header': True,
            'harmonization': super().get_harmonization_config()
        }

    def test_CSV_creation(self, file1, parameters):
        with CSV.create(file1, **parameters) as csv:
            assert csv.num_lines == 3
            assert all(column in csv for column in ['column1', 'column2', 'column3'])

            counter = 0
            for index, line in csv:
                counter += 1
                assert index + 1 == counter  # Validate index
                assert len(line) == 3  # Validate all cells are returned
                assert all(f"{counter}." in cell for (index, cell) in line)  # Validate correct cells are returned

            # Ensure all three lines are read
            assert counter == 3

    def test_CSV_no_header(self, file1, parameters):
        parameters['has_header'] = False
        columns = ['column1', 'column2', 'column3']

        with CSV.create(file1, **parameters) as csv:

            assert csv.num_lines == 4
            assert all(column not in csv for column in columns)

            for index, (line_index, line) in enumerate(csv):
                if line_index == 0:
                    assert line.cells == columns

            assert index == 3

    def test_CSV_max_lines(self, file1, parameters):
        parameters['loadLinesMax'] = 2

        with CSV.create(file1, **parameters) as csv:
            assert csv.num_lines == 3

            for index, (line_index, _) in enumerate(csv):
                pass

            # Ensure that only 2 records are returned
            assert index == 1
            assert line_index == 1

    def test_CSV_skip_initial_space(self, file1, parameters):
        # Test config with has_header and without
        for has_header, skipInitialSpace in [(False, 2), (True, 1)]:
            parameters['has_header'] = has_header
            parameters['skipInitialSpace'] = skipInitialSpace

            with CSV.create(file1, **parameters) as csv:
                counter = 2
                for line_index, line in csv:
                    assert all(f"{counter}." in cell for (index, cell) in line)  # Validate correct cells are returned
                    counter += 1

                assert line_index == 1
