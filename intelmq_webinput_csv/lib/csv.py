import csv
import itertools
import collections

from pathlib import Path
from typing import Union, Tuple, List

from intelmq.lib.message import Event
from intelmq.lib.utils import RewindableFileHandle
from intelmq.lib.exceptions import IntelMQException, IntelMQHarmonizationException

from .exceptions import InvalidCellException
from . import util


class CSV:
    """ CSV reader helper class

    Contains encapsulating functions for easily reading the CSV files
    """

    def __init__(self, file: Union[Path, str], delimiter: str, quotechar: str, escapechar: str,
                 skipInitialSpace: int, loadLinesMax: int, has_header: bool,
                 columns: Union[None, list], **kwargs):
        self.delimiter = delimiter
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

        # TODO: validate more efficient method
        with self.file.open('r') as handle:
            self.num_lines = len(handle.readlines())

        if self.has_header:
            self.num_lines -= 1

        self.line_index = 0
        self.parameters = kwargs

        # add harmonization to parameters
        if 'harmonization' not in self.parameters:
            self.parameters['harmonization'] = util.load_harmonization_config()

    def __enter__(self):
        self.handle = RewindableFileHandle(self.file.open('r', encoding='utf-8'))
        self.reader = csv.reader(self.handle, delimiter=self.delimiter,
                                 quotechar=self.quotechar,
                                 skipinitialspace=self.skipInitialSpace,
                                 escapechar=self.escapechar
                      )

        if self.has_header:
            first_line = next(self.reader)
            self.columns_raw = self.handle.current_line.strip('\n')

            if not self.columns:
                self.columns = first_line

        # Skip initial n lines
        if self.skipInitialSpace:
            for _ in range(self.skipInitialSpace):
                next(self.reader)

        return self

    def __exit__(self, _exc_type, _exc_value, _exc_traceback):
        self.handle.f.close()

    def __contains__(self, other):
        result = (self.columns and other in self.columns)
        return result

    def __iter__(self):
        return self

    def __len__(self):
        return self.num_lines

    def __next__(self):
        line = next(self.reader)

        # Escape any escapechar
        line = CSVLine(
            cells=line,
            columns=self.columns,
            index=self.line_index,
            raw=self.handle.current_line,
            **self.parameters
        )

        # if max lines read, stop!
        self.line_index += 1
        if self.max_lines and self.line_index > self.max_lines:
            raise StopIteration

        return line

    @staticmethod
    def create(*args, **kwargs):
        return CSV(*args, **kwargs)


class CSVLine():

    def __init__(self, cells: list = [], columns: Union[None, dict] = {}, index: int = -1, raw: str = None,
                 **kwargs):
        self.raw = raw.strip('\n') if raw else raw
        self.cells = cells
        self.index = index
        self.columns = columns

        self.parameters = kwargs
        self.validation = False
        self.event = Event(harmonization=kwargs.pop('harmonization'))

        # Calculate real index in file
        self.real_index = sum([
            self.index,
            self.parameters.get('skipInitialSpace', 0),
            int(self.parameters.get('has_header', False))
        ])

    def __str__(self):
        if self.raw:
            return self.raw
        else:
            return ','.join(self.cells)

    def __iter__(self):
        # Use Tuple columns, cell or None,cell
        columns = self.columns if self.columns else itertools.repeat(None)
        return zip(columns, self.cells)

    def items(self) -> dict:
        """ Generate key:value pairs for all cells/columns

        Returns:
            dict: with column - value 
        """
        # Loop through all columns and cells
        for (column, value) in self:
            # Skip empty columns or cells
            if not column or not value:
                continue

            yield (column, value)

    def _event_add(self, key: str, value: str, overwrite: bool = False):
        """ Add field to IntelMQ Event

        Parameters
            key: field key for setting value
            value: value to set
            overwrite: overwrite any existing value
        """
        try:
            if overwrite or key not in self.event:
                self.event.add(key, value)

        except IntelMQHarmonizationException as ihe:
            ice = InvalidCellException(ihe, self)

            if self.validation:
                self.invalid_cells.append(ice)
            else:
                raise ice

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
            value = util.parse_time(value, timezone=self.parameters['timezone'])
        elif column == 'extra':
            value = util.handle_extra(value)

        self._event_add(column, value)

    def validate(self) -> Tuple[Event, List[InvalidCellException]]:
        """ Validates current CSV line

        Returns:
            (Event, Exceptions): Parsed IntelMQ Event and list of InvalidCSVLineExceptions
        Raises:
            InvalidCSVLineException if invalid line or cell has been detected

        """
        self.validation = True
        self.invalid_cells = []
        self._verify_columns()

        event = self.parse()

        self.validation = False
        return (event, self.invalid_cells)

    def parse(self) -> Union[None, Event]:
        """ Parse all cells in current line

        Returns:
            Event: filled IntelMQ Event or None if exception occured
        """
        self._verify_columns()

        # Parse all cells in row
        for (column, value) in self.items():
            self.parse_cell(value, column)

        # Set any custom fields
        fields = collections.ChainMap(
            self.parameters.get('constant_fields', {}),
            self.parameters.get('custom_input_fields', {})
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
