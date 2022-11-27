import csv
import itertools
import collections

from pathlib import Path
from typing import Union

from intelmq.lib.message import Event
from intelmq.lib.utils import RewindableFileHandle
from intelmq.lib.exceptions import IntelMQException
from . import util


class CSV:
    """ CSV reader helper class

    Contains encapsulating functions for easily reading the CSV files
    """

    def __init__(self, file: Union[Path, str], delimiter: str, quotechar: str, escapechar: str,
                 skipInitialSpace: int, loadLinesMax: int, has_header: bool, 
                 columns: Union[None, list], **kwargs):
        self.delimeter = delimiter
        self.quotechar = quotechar
        self.escapechar = escapechar
        self.skipInitialSpace = skipInitialSpace
        self.max_lines = loadLinesMax
        self.has_header = has_header
        self.columns = columns

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
        self.parameters = kwargs

    def __enter__(self):
        self.handle = RewindableFileHandle(self.file.open('r', encoding='utf-8'))
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
        line = CSVLine(
            cells=line,
            columns=self.columns,
            index=line_index,
            raw=self.handle.current_line,
            **self.parameters
        )

        # if max lines read, stop!
        if self.max_lines and self.line_index > self.max_lines:
            raise StopIteration

        return (line_index, line)

    @staticmethod
    def create(*args, **kwargs):
        return CSV(*args, **kwargs)


class CSVLine():

    def __init__(self, cells: list = [], columns: Union[None, dict] = {}, index: int = -1, raw: str = None,
                 **kwargs):
        self.raw = raw
        self.cells = cells
        self.index = index
        self.columns = columns

        self.parameters = kwargs
        self.event = Event(harmonization=kwargs.get('harmonization'))

    def __str__(self):
        if self.raw:
            return self.raw
        else:
            return ','.join(self.cells)

    def __iter__(self):
        # Use Tuple columns, cell or None,cell
        columns = self.columns if self.columns else itertools.repeat(None)
        return zip(columns, self.cells)

    def _event_add(self, key: str, value: str, overwrite: bool = False):
        """ Add field to IntelMQ Event

        Parameters
            key: field key for setting value
            value: value to set
            overwrite: overwrite any existing value
        """
        if overwrite or key not in self.event:
            self.event.add(key, value)

    def _verify_columns(self):
        """ Ensure that columns have been defined

        Raises:
            IntelMQException if no columns has been specified
        """
        if not self.columns:
            raise IntelMQException("Columns have not been specified")

    def __len__(self):
        return len(self.cells)

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

        self._event_add(column, value)

    def validate(self) -> bool:
        """ Validates current CSV line

        Returns:
            True or False whether is valid CSV line
        """
        try:
            self._verify_columns()
            self.parse()

            return True
        except Exception:
            return False

    def parse(self) -> Union[None, Event]:
        """ Parse all cells in current line

        Returns:
            Event: filled IntelMQ Event or None if exception occured
        """
        self._verify_columns()

        # Parse all cells in row
        for (column, value) in self:
            # Skip empty columns or cells
            if not column or not value:
                continue

            self.parse_cell(value, column)

        # Set any custom fields
        fields = collections.ChainMap(
            self.parameters.get('constant_fields', {}),
            {k[7:]: v for k, v in self.parameters.items() if k.startswith('custom_')}
        )

        for key, value in fields.items():
            self._event_add(key, value)

        # Save raw field
        self._event_add('raw', self.raw)

        # set any required fields
        required = ['classification.type', 'classification.identifier', 'feed.code'
                    'time.observation']
        for key in required:
            if self.parameters.get(key):
                self._event_add(key, self.parameters[key])

        return self.event
