import re
from typing import TYPE_CHECKING

from intelmq.lib.exceptions import IntelMQException, IntelMQHarmonizationException, InvalidValue

# To prevent circular import
if TYPE_CHECKING:
    from intelmq_webinput_csv.lib.csv import CSVLine


class InvalidCellException(IntelMQException):
    """ General class for handling InvalidValue Exception in CSVLine
    """

    def __init__(self, invalid: IntelMQHarmonizationException, line: 'CSVLine', **kwargs):
        self.line = line
        self.invalid = invalid

        # Determine value/key (column) from exception
        if isinstance(invalid, InvalidValue):
            regex = r".*value '(?P<value>.+)'.*for\skey\s'(?P<key>[\w\.]+)'.*"
        else:
            regex = r".*key\s'(?P<key>[\w\.]+)'.*"

        match = re.match(regex, str(invalid))

        if not match:
            raise Exception(f"Cannot parse {self.invalid.__class__.__name__} Exception: {self.invalid}")

        # Add attributes for all named groups found in regex
        self.__dict__.update(match.groupdict())

        # Determine indexes of line within CSV and index of column
        self.line_index = line.index
        self.column_index = line.columns.index(self.key) if line.columns and hasattr(self, 'key') else -1

        self.message = f"Invalid CSV line[{self.line.index}:{self.line.real_index}] due: {self.invalid}"
