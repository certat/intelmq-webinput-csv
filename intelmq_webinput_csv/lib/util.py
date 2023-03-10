from __future__ import annotations  # Prevent circular import for type checking, default Pythonv3.11

import uuid
import csv
import json
import random
import time

from typing import Union, List, TYPE_CHECKING
from datetime import date
from pathlib import Path

import dateutil.parser
from flask import current_app as app

from intelmq_webinput_csv.version import __version__
from intelmq import VAR_STATE_PATH
from intelmq import HARMONIZATION_CONF_FILE
from intelmq.lib.message import Event
from intelmq.lib.utils import load_configuration
from intelmq.lib.pipeline import PipelineFactory, Pipeline

if TYPE_CHECKING:
    from intelmq_webinput_csv.lib.csv import CSV, CSVLine

PIPELINE = None
HARMONIZATION_CONF = None
PARAMETERS = {
    'pipeline': '',
    'uuid': '',
    'uuid': '',
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


def parse_time(value: str, timezone: Union[str, None] = None) -> date:
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
    parameters.setdefault('CUSTOM_INPUT_FIELDS', {})

    parameters.setdefault('CUSTOM_INPUT_FIELDS', {})

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

    # Set any custom_key fields
    for key, value in form.items():
        if key.startswith('custom_'):
            key = key[7:]  # remove prefix `custom_`
            custom_fields = parameters.get('CUSTOM_INPUT_FIELDS', {})
            custom_fields[key] = value

    # Set any custom_key fields
    for key, value in form.items():
        if key.startswith('custom_'):
            key = key[7:]  # remove prefix `custom_`
            custom_fields = parameters.get('CUSTOM_INPUT_FIELDS', {})
            custom_fields[key] = value
    return parameters


def cleanup_tempdir(age: int = 5):
    """ Cleanup old files in tmpdir

    Parameters:
        age: int indicating when files are old enough to be deleted
    """
    current = time.time()
    dir = app.config.get('VAR_STATE_PATH', VAR_STATE_PATH)
    second_delta = age * 24 * 60 * 60  # day * hours * minutes * seconds

    for child in Path(dir).glob("*.csv"):

        if not child.is_file():
            continue

        m_time = child.stat().st_mtime
        if m_time < (current - second_delta):
            child.unlink(missing_ok=True)


def get_temp_file(filename: str = 'webinput_csv', prefix: str = None, extension: str = 'csv', **kwargs) -> Path:
    """ Get path to temporary file

    Parameters:
        filename (str): name of temporary file
        prefix (str): to prepend for filename
        extension (str): file extension to use

    Returns:
        Path: object to temp file
    """
    dir = app.config.get('VAR_STATE_PATH', VAR_STATE_PATH)

    filename = f"{filename}.{extension}"
    if prefix:
        filename = f"{prefix}_{filename}"

    return Path(dir) / filename

def calculate_segments(reader):
    segments = round(len(reader) / 100)
    segments += random.randint(1, 9)  # Make the proces update bit more randomised
    return segments

def create_pipeline(pipeline, connect: bool = True, event: Event = None) -> Pipeline:
    """ Create Pipeline object

    Parameters:
        pipeline (str): Name of queue to connect to
        connect (bool): whether to connect
        event (Event): event to format queue

    Returns:
        Pipeline object
    """
    global PIPELINE

    # If pipeline is not defined, no options are given, so use configured pipeline
    if not pipeline:
        pipeline = app.config['DESTINATION_PIPELINE_QUEUE']

    # Format pipeline if configured
    if app.config.get('DESTINATION_PIPELINE_QUEUE_FORMATTED', False):
        pipeline = pipeline.format(ev=event)

    # Singleton for Pipeline object
    if not PIPELINE:
        PIPELINE = PipelineFactory.create(
            pipeline_args=app.config['INTELMQ'],
            logger=app.logger,
            direction='destination'
        )

        # Load config and connect in Singleton
        PIPELINE.load_configurations('destination')
        PIPELINE.connect()

    # Ensure that Pipeline has correct destination queue
    if pipeline not in PIPELINE.destination_queues.get('_default', []):
        PIPELINE.set_queues(pipeline, "destination")

    return PIPELINE


def generate_uuid() -> str:
    """ Generate a UUID

    Returns:
        str: random UUID
    """
    return uuid.uuid4()


def save_failed_csv(reader: CSV, lines: List[CSVLine], session=dict()):
    """
    Save all invalid lines to a seperate CSV file

    Parameters:
        reader(CSV): CSV object used to read the lines
        lines (List[CSVLine]): list of invalid lines
        session (dict): Flask session obj
    """
    invalid_file = get_temp_file(filename='webinput_invalid_csv.csv')

    with invalid_file.open('w+') as f:
        # Filter out all None columns
        columns = [c for c in reader.columns if c]

        writer = csv.DictWriter(
            f,
            fieldnames=columns,
            delimiter=reader.delimiter,
            quotechar=reader.quotechar,
            escapechar=reader.escapechar
        )

        writer.writeheader()

        for line in lines:
            result = dict(line.items())
            writer.writerow(dict(line.items()))
def calculate_segments(reader):
    segments = round(len(reader) / 100)
    segments += random.randint(1, 9)  # Make the proces update bit more randomised
    return segments

