import json

from typing import Union, List
from datetime import date
from pathlib import Path

import dateutil.parser
from flask import current_app as app

from intelmq_webinput_csv.version import __version__
from intelmq import VAR_STATE_PATH
from intelmq import HARMONIZATION_CONF_FILE
from intelmq.lib.utils import load_configuration
from intelmq_webinput_csv.lib.csv import CSV, CSVLine

HARMONIZATION_CONF = None
PARAMETERS = {
    'timezone': '+00:00',
    'classification.type': 'test',
    'classification.identifier': 'test',
    'feed.code': 'custom',
    'delimiter': ',',
    'has_header': '"false"',
    'quotechar': '\"',
    'escapechar': '\\',
    'columns': [],
    'use_column': [],
    'dryrun': '"true"',
    'skipInitialSpace': '"false"',
    'skipInitialLines': 0,
    'loadLinesMax': 100,
}


def load_config(config_file):
    """ Load config from file

    Parameters:
        config_file (Readable): read config file

    Returns:
        dict: with config with keys all in UPPER
    """
    config = json.load(config_file)
    new_config = {k.upper(): v for k, v in config.items()}

    # Ensure that BASE_URL is correctly translated to Flask Application Root
    new_config['APPLICATION_ROOT'] = new_config.get('BASE_URL', '/')

    if len(new_config['APPLICATION_ROOT']) > 1 and new_config['APPLICATION_ROOT'].endswith('/'):
        new_config['APPLICATION_ROOT'] = new_config['APPLICATION_ROOT'][:-1]

    new_config['VERSION'] = __version__

    return new_config


def load_harmonization_config(load_json: bool = False) -> dict:
    """ Load Harmonization config

    Implements Singleton functionality for loading config only once

    Parameters:
        load_json (bool): whether to load the config as JSON

    Returns:
        dict of Harmonization config
    """
    global HARMONIZATION_CONF

    harmonization_file = app.config.get('HARMONIZATION_CONF_FILE', HARMONIZATION_CONF_FILE)

    if not HARMONIZATION_CONF:
        HARMONIZATION_CONF = load_configuration(harmonization_file)

    if load_json:
        with open(harmonization_file) as handle:
            return json.load(handle)
    else:
        return HARMONIZATION_CONF


def parse_time(value: str, timezone: Union[str, None]) -> date:
    """ Parse date string

    Parameters:
        value: string to parse to date
        timezone: additional timezone info

    Returns:
        Date object
    """
    parsed = dateutil.parser.parse(value, fuzzy=True)

    if not parsed.tzinfo and timezone:
        value += timezone
        parsed = dateutil.parser.parse(value)

    return parsed.isoformat()


def handle_extra(value: str) -> dict:
    """ Handle extras

    >>> handle_extra('foobar')
    {'data': 'foobar'}
    >>> handle_extra('{"data": "foobar"}')
    {'data': 'foobar'}
    >>> handle_extra('')
    >>> handle_extra('["1", 2]')
    {'data': ['1', 2]}

    Parameters:
        value: any string

    Returns:
        dictionary
    """
    try:
        value = json.loads(value)
    except ValueError:
        if not value:
            return
        value = {'data': value}
    else:
        if not isinstance(value, dict):
            value = {'data': value}
    return value


def handle_parameters(form):
    parameters = {}
    for key, default_value in app.config.items():
        parameters[key] = form.get(key, default_value)
    for key, value in PARAMETERS.items():
        parameters[key] = form.get(key, value)
    parameters['dryrun'] = json.loads(parameters['dryrun'])
    if parameters['dryrun']:
        parameters['classification.type'] = 'test'
        parameters['classification.identifier'] = 'test'
    if type(parameters['columns']) is not list and parameters['use_column']:
        parameters['use_column'] = [json.loads(a.lower()) for a in
                                    parameters['use_column'].split(',')]
        parameters['columns'] = parameters['columns'].split(',')
    parameters['columns'] = [a if b else None for a, b in
                             zip(parameters['columns'],
                                 parameters['use_column'])]
    parameters['skipInitialLines'] = int(parameters['skipInitialLines'])
    parameters['skipInitialSpace'] = json.loads(parameters['skipInitialSpace'])
    parameters['has_header'] = json.loads(parameters['has_header'])
    parameters['loadLinesMax'] = int(parameters['loadLinesMax'])
    return parameters


def get_temp_file(filename: str = 'webinput_csv.csv') -> Path:
    """ Get path to temporary file

    Parameters:
        filename (str): name of temporary file

    Returns:
        Path: object to temp file
    """
    dir = app.config.get('VAR_STATE_PATH', VAR_STATE_PATH)
    return Path(dir) / filename


def save_failed_csv(reader: CSV, lines: List[CSVLine]):
    """
    Save all invalid lines to a seperate CSV file

    Parameters:
        reader(CSV): CSV object used to read the lines
        lines (List[CSVLine]): list of invalid lines
    """
    invalid_file = get_temp_file(filename='webinput_invalid_csv.csv')

    with invalid_file.open('w+', encoding='utf-8') as f:
        f.write(f"{reader.columns_raw}\n")

        for line in lines:
            f.write(f"{line.raw}\n")
