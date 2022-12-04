import os
import json

from typing import Union
from datetime import date
from pathlib import Path

import dateutil.parser

from flask import jsonify, make_response
from intelmq import VAR_STATE_PATH

TEMP_FILE = os.path.join('/config/configs/webinput', 'webinput_csv.temp')
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

CONFIG_FILE = os.path.join('/config/configs/webinput', 'webinput_csv.conf')
with open(CONFIG_FILE) as handle:
    CONFIG = json.load(handle)
    BASE_URL = CONFIG.get('base_url', '')
    if BASE_URL.endswith('/'):
        BASE_URL = BASE_URL[:-1]


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
    for key, default_value in CONFIG.items():
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


def create_response(text, content_type=None):
    is_json = False
    if not isinstance(text, str):
        text = jsonify(text)
        is_json = True
    response = make_response(text)
    if is_json:
        response.mimetype = 'application/json'
        response.headers['Content-Type'] = "text/json; charset=utf-8"
    if content_type:
        response.headers['Content-Type'] = content_type
    response.headers['Access-Control-Allow-Origin'] = "*"
    return response


def get_temp_file(filename: str = 'webinput_csv.csv') -> Path:
    return Path(VAR_STATE_PATH) / filename
