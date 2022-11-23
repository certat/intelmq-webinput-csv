import csv
import collections

from pathlib import Path
from typing import Union, Iterable, Tuple

from intelmq.lib.message import Event
from .lib import util

class CSV:
    """ CSV reader helper class
    
    Contains encapsulating functions for easily reading the CSV files
    """

    def __init__(self, file: Union[Path, str], delimiter: str, quotechar: str, escapechar: str, 
                    skipInitialSpace: int, loadLinesMax: int, has_header: bool, **kwargs):
        self.delimeter = delimiter
        self.quotechar = quotechar
        self.escapechar = escapechar
        self.skipInitialSpace = skipInitialSpace
        self.max_lines = loadLinesMax
        self.has_header = has_header
        self.columns = None

        # Ensure file is Path obj
        if isinstance(file, str):
            self.file = Path(file)
        else:
            self.file = file

        with self.file.open('rb') as handle:
            self.num_lines = handle.read().count(b'\n')

        if self.has_header:
            self.num_lines -= 1

        self.line_index = 0

    def __enter__(self):
        self.handle = self.file.open('r', encoding='utf-8')
        self.reader = csv.reader(self.handle, delimiter=self.delimeter,
                            quotechar=self.quotechar,
                            skipinitialspace=self.skipInitialSpace,
                            escapechar=self.escapechar
                            )

        # Skip header if present
        if self.has_header:
            self.columns = next(self.reader)

        # Skip initial lines
        if self.skipInitialSpace:
            for _ in range(self.skipInitialSpace):
                next(self.reader)

        return self

    def __exit__(self, _exc_type, _exc_value, _exc_traceback):
        self.handle.close()

    def __contains__(self, other):
        result = (self.columns and other in self.columns)
        return result

    def __iter__(self):
        return self

    def __next__(self):
        line = next(self.reader)
        line_index = self.line_index
        self.line_index += 1

        # Escape any escapechar
        line = [cell.replace(self.escapechar*2, self.escapechar) for cell in line]

        # if max lines read, stop!
        if self.max_lines and self.line_index > self.max_lines:
            raise StopIteration

        return (line_index, line)

    @staticmethod
    def create(*args, **kwargs):
        return CSV(*args, **kwargs)

class CSVLine():

    def __init__(self, cells: Union[None, list], columns: Union[None, dict],
                    harmonization_config: Union[None, dict], **kwargs):
        self.cells = cells
        self.columns = columns
        self.event = Event(harmonization=harmonization_config)
        self.parameters = kwargs

    def __iter__(self):
        return self

    def __next__(self) -> Iterable[Tuple[str, str]]:
        for column, value in zip(self.columns, self.cells):
            yield (column, value)

    def event_add(self, key: str, value: str, overwrite: bool=False):
        """ Add field to IntelMQ Event

        Parameters
            key: field key for setting value
            value: value to set
            overwrite: overwrite any existing value
        """
        if overwrite or key not in self.event:
            self.event.add(key, value)

    def parse_cell(self, value: str, column: str):
        """ Parse a single cell

        Parameters:
            value: value of cell
            column: column name
        """

        if column.startswith('time.'):
            value = util.parse_time(value)
        elif column == 'extra':
            value = util.handle_extra(value)
        
        self.event_add(column, value)

    def parse(self) -> Union[None, Event]:
        """ Parse all cells in current line

        Returns:
            Event: filled IntelMQ Event or None if exception occured
        """
        try:
            # Parse all cells in row
            for column, value in self:
                # Skip empty columns or cells
                if not column or not value:
                    continue

                self.parse_cell(value, column)

            self.custom = {}

            # Set any custom fields
            fields = collections.ChainMap(
                self.parameters.get('constant_fields', {}),
                {k[7:]: v for k, v in self.custom.items() if k.startswith('custom_')}
            )

            for key, value in fields.items():
                self.event_add(key, value)

            # set any required fields
            required = ['classification.type', 'classification.identifier', 'feed.code'
                        'time.observation']
            for key in required:
                if self.parameters.get(key):
                    self.event_add(key, self.parameters[key])
        except Exception 

        return self.event