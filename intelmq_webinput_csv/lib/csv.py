import csv

from typing import Union
from pathlib import Path

class CSV:
    """ CSV reader helper class
    
    Contains encapsulating functions for easily reading the CSV files
    """

    def __init__(self, file: Union[Path, str], delimiter: str, quotechar: str, escapechar: str, 
                    skipInitialSpace: int, loadLinesMax: int, **kwargs):
        self.delimeter = delimiter
        self.quotechar = quotechar
        self.escapechar = escapechar
        self.skipInitialSpace = skipInitialSpace
        self.max_lines = loadLinesMax
        self.columns = None

        # Ensure file is Path obj
        if isinstance(file, str):
            self.file = Path(file)
        else:
            self.file = file

        with self.file.open('r', encoding='utf-8') as handle:
            self.num_lines = handle.read().count(b'/n')

        if self.has_header:
            self.num_lines -= 1

        self.line_index = 0

    def __enter__(self):
        handle = self.file.open('r', encoding='utf-8')
        self.reader = csv.reader(handle, delimiter=self.delimeter,
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

    def __close__(self):
        self.file.close()

    def __contains__(self, other):
        result = (self.columns and other in self.columns)
        return result

    def __iter__(self):
        self.reader()

    def __next__(self):
        line = next(self.reader)
        line_index = self.line_index
        self.line_index += 1

        # Escape any escapechar
        line = line.replace(self.escapechar*2, self.escapechar)

        # if max lines read, stop!
        if self.max_lines and self.line_index > self.line_index:
            raise StopIteration

        return (line_index, line)

    @staticmethod
    def create(**kwargs):
        return CSV(**kwargs)