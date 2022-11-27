import os

from pathlib import Path
from intelmq.lib.utils import load_configuration


class BaseTest:

    def get_fixtures_path(self) -> Path:
        """ Get Path obj for fixtures directory

        Returns:
            Path object to directory
        """
        path_current_test = os.getenv('PYTEST_CURRENT_TEST').split(':')[0]
        test_dir = Path(path_current_test)

        # Current test is somewhere in subdirectory of 'tests',
        # go up until tests directory is found
        while test_dir.stem != 'tests':
            test_dir = test_dir.parent

        return (test_dir / 'fixtures').absolute()

    def get_harmonization_config(self, file_name: str='harmonization.conf') -> dict:
        """ Load harmonization config

        Parameters:
            file_name: name of harmonization config to use
        
        Returns:
            Dict of parsed harmonization config
        """
        configuration_filepath = self.get_fixtures_path() / file_name
        return load_configuration(configuration_filepath)
