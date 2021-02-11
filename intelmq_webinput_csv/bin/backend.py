# -*- coding: utf-8 -*-
# Copyright (c) 2017-2018 nic.at GmbH <wagner@cert.at>
# SPDX-License-Identifier: AGPL-3.0
import csv
import json
import pickle
import pkg_resources
import traceback
import logging
import os

import dateutil.parser
from flask import Flask, jsonify, make_response, request

from intelmq import HARMONIZATION_CONF_FILE, CONFIG_DIR, VAR_STATE_PATH
from intelmq.lib.harmonization import DateTime, IPAddress
from intelmq.bots.experts.taxonomy.expert import TAXONOMY
from intelmq.lib.message import Event, MessageFactory
from intelmq.lib.pipeline import PipelineFactory
from intelmq.lib.exceptions import InvalidValue, KeyExists
from intelmq.lib.utils import RewindableFileHandle

from intelmq_webinput_csv.version import __version__


CONFIG_FILE = os.path.join(CONFIG_DIR, 'webinput_csv.conf')
logging.info('Reading configuration from %r.', CONFIG_FILE)
with open(CONFIG_FILE) as handle:
    CONFIG = json.load(handle)
    BASE_URL = CONFIG.get('base_url', '')
    if BASE_URL.endswith('/'):
        BASE_URL = BASE_URL[:-1]
TEMP_FILE = os.path.join(VAR_STATE_PATH, '../webinput_csv.temp')


CUSTOM_FIELDS_HTML_TEMPLATE = """
<div class="field">
    <div class="control">
        <label class="label">{name}</label>
        <input class="input" type="text" placeholder="{name}" v-model="previewFormData.{jsname}">
    </div>
</div>"""
CUSTOM_FIELDS_JS_DEFAULT_TEMPLATE = "{jsname}: '{default}',"
CUSTOM_FIELDS_JS_FORM_TEMPLATE = "formData.append('custom_{name}', this.previewFormData.{jsname});"
custom_fields_html = []
custom_fields_js_default = []
custom_fields_js_form = []
for key, value in CONFIG.get('custom_input_fields', {}).items():
    jskey = 'custom' + key.title().replace('.', '')
    custom_fields_html.append(CUSTOM_FIELDS_HTML_TEMPLATE.format(name=key, jsname=jskey))
    custom_fields_js_default.append(CUSTOM_FIELDS_JS_DEFAULT_TEMPLATE.format(jsname=jskey, default=value))
    custom_fields_js_form.append(CUSTOM_FIELDS_JS_FORM_TEMPLATE.format(name=key, jsname=jskey))


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
STATIC_FILES = {
    'js/preview.js': None,
    'js/upload.js': None,
    'preview.html': None,
    'index.html': None,
    }

for static_file in STATIC_FILES.keys():
    filename = pkg_resources.resource_filename('intelmq_webinput_csv', 'static/%s' % static_file)
    with open(filename, encoding='utf8') as handle:
        STATIC_FILES[static_file] = handle.read()
        if static_file.startswith('js/') or static_file.endswith('.html'):
            STATIC_FILES[static_file] = STATIC_FILES[static_file].replace('__BASE_URL__', BASE_URL)
            STATIC_FILES[static_file] = STATIC_FILES[static_file].replace('__VERSION__', __version__)
        if static_file == 'preview.html':
            STATIC_FILES[static_file] = STATIC_FILES[static_file].replace('__CUSTOM_FIELDS_HTML__',
                                                                          '\n'.join(custom_fields_html))
        if static_file == 'js/preview.js':
            STATIC_FILES[static_file] = STATIC_FILES[static_file].replace('__CUSTOM_FIELDS_JS_DEFAULT__',
                                                                          '\n'.join(custom_fields_js_default))
            STATIC_FILES[static_file] = STATIC_FILES[static_file].replace('__CUSTOM_FIELDS_JS_FORM__',
                                                                          '\n'.join(custom_fields_js_form))


app = Flask('intelmq_webinput_csv')


with open(HARMONIZATION_CONF_FILE) as handle:
    EVENT_FIELDS = json.load(handle)


class PipelineParameters(object):
    def __init__(self):
        for key, value in CONFIG['intelmq'].items():
            setattr(self, key, value)


def write_temp_file(data):
    """
    Write metadata about the current active file.
    filename, total_lines
    """
    with open(TEMP_FILE, 'wb') as handle:
        pickle.dump(data, handle)


def get_temp_file():
    """
    Opposite of write_temp_file
    """
    try:
        with open(TEMP_FILE, 'rb') as handle:
            data = pickle.load(handle)
            if len(data) == 2:
                return data
    except TypeError:  # TypeError: returned value has no len()
        return False
    return False


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


def handle_extra(value: str) -> dict:
    """
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


@app.route('/')
def form():
    response = make_response(STATIC_FILES['index.html'])
    response.mimetype = 'text/html'
    response.headers['Content-Type'] = "text/html; charset=utf-8"
    return response


@app.route('/plugins/<path:page>')
def plugins(page):
    filename = pkg_resources.resource_filename('intelmq_webinput_csv', 'static/plugins/%s' % page)
    with open(filename, mode='rb') as handle:
        response = make_response(handle.read())
    if page.endswith('.js'):
        response.mimetype = 'application/x-javascript'
        response.headers['Content-Type'] = "application/x-javascript; charset=utf-8"
    elif page.endswith('.css'):
        response.mimetype = 'text/css'
        response.headers['Content-Type'] = "text/css; charset=utf-8"
    return response


@app.route('/js/<page>')
def js(page):
    response = make_response(STATIC_FILES['js/%s' % page])
    response.mimetype = 'application/x-javascript'
    response.headers['Content-Type'] = "application/x-javascript; charset=utf-8"
    return response


@app.route('/upload', methods=['POST'])
def upload_file():
    success = False
    filename = os.path.join(VAR_STATE_PATH, '../webinput_csv.csv')
    if 'file' in request.files and request.files['file'].filename:
        request.files['file'].save(filename)
        request.files['file'].stream.seek(0)
        total_lines = request.files['file'].stream.read().count(b'\n')  # we don't care about headers here
        success = True
    elif 'text' in request.form and request.form['text']:
        with open(filename, mode='w', encoding='utf8') as handle:
            handle.write(request.form['text'])
        success = True
        total_lines = len(request.form['text'].splitlines())
    if not success and request.form.get('use_last_file', False):
        success = True
        filename, total_lines = get_temp_file()
    elif success:
        write_temp_file((filename, total_lines))
    if not success:
        return create_response('no file or text')

    parameters = handle_parameters(request.form)
    if parameters['has_header']:
        total_lines -= 1
    preview = []
    valid_ip_addresses = None
    valid_date_times = None
    lineindex = line = None
    try:
        with open(filename, encoding='utf8') as handle:
            reader = csv.reader(handle, delimiter=parameters['delimiter'],
                                quotechar=parameters['quotechar'],
                                skipinitialspace=parameters['skipInitialSpace'],
                                escapechar=parameters['escapechar'],
                                )
            for lineindex, line in enumerate(reader):
                line = [col.replace(parameters['escapechar']*2, parameters['escapechar']) for col in line]
                if parameters['skipInitialLines']:
                    if parameters['has_header'] and lineindex == 1:
                        for _ in range(parameters['skipInitialLines']):
                            line = next(reader)
                    elif not parameters['has_header'] and lineindex == 0:
                        for _ in range(parameters['skipInitialLines']):
                            line = next(reader)
                if lineindex >= parameters['loadLinesMax'] + parameters['has_header']:
                    break
                if valid_ip_addresses is None:  # first data line
                    valid_ip_addresses = [0] * len(line)
                    valid_date_times = [0] * len(line)
                for columnindex, value in enumerate(line):
                    if IPAddress.is_valid(value):
                        valid_ip_addresses[columnindex] += 1
                    if DateTime.is_valid(value):
                        valid_date_times[columnindex] += 1
                preview.append(line)
    except Exception as exc:
        preview = [['Parse Error'], ['Is the number of columns consistent?']] + \
            [[x] for x in traceback.format_exc().splitlines()] + \
            [['Current line (%d):' % lineindex]] + \
            [line]
    column_types = ["IPAddress" if x/(total_lines if total_lines else 1) > 0.7 else None for x in valid_ip_addresses]
    column_types = ["DateTime" if valid_date_times[i]/(total_lines if total_lines else 1) > 0.7 else x for i, x in enumerate(column_types)]
    return create_response({"column_types": column_types,
                            "use_column": [bool(x) for x in column_types],
                            "preview": preview,
                            })


@app.route('/preview', methods=['GET', 'POST'])
def preview():
    if request.method == 'GET':
        response = make_response(STATIC_FILES['preview.html'])
        response.mimetype = 'text/html'
        response.headers['Content-Type'] = "text/html; charset=utf-8"
        return response

    parameters = handle_parameters(request.form)
    tmp_file = get_temp_file()
    if not tmp_file:
        app.logger.info('no file')
        return create_response('No file')
    retval = []
    lines_valid = 0
    with open(tmp_file[0], encoding='utf8') as handle:
        reader = csv.reader(handle, delimiter=parameters['delimiter'],
                            quotechar=parameters['quotechar'],
                            skipinitialspace=parameters['skipInitialSpace'],
                            escapechar=parameters['escapechar'],
                            )
        if parameters['has_header']:
            next(reader)
        for _ in range(parameters['skipInitialLines']):
            next(reader)
        for lineindex, line in enumerate(reader):
            event = Event()
            line_valid = True
            for columnindex, (column, value) in \
                    enumerate(zip(parameters['columns'], line)):
                if not column or not value:
                    continue
                if column.startswith('time.'):
                    try:
                        parsed = dateutil.parser.parse(value, fuzzy=True)
                        if not parsed.tzinfo:
                            value += parameters['timezone']
                            parsed = dateutil.parser.parse(value)
                        value = parsed.isoformat()
                    except ValueError:
                        line_valid = False
                if column == 'extra':
                    value = handle_extra(value)
                try:
                    event.add(column, value)
                except (InvalidValue, KeyExists) as exc:
                    retval.append((lineindex, columnindex, value, str(exc)))
                    line_valid = False
            for key, value in parameters.get('constant_fields', {}).items():
                if key not in event:
                    try:
                        event.add(key, value)
                    except InvalidValue as exc:
                        retval.append((lineindex, -1, value, str(exc)))
                        line_valid = False
            for key, value in request.form.items():
                if not key.startswith('custom_'):
                    continue
                key = key[7:]
                if key not in event:
                    try:
                        event.add(key, value)
                    except InvalidValue as exc:
                        retval.append((lineindex, -1, value, str(exc)))
                        line_valid = False
            try:
                if CONFIG.get('destination_pipeline_queue_formatted', False):
                    CONFIG['destination_pipeline_queue'].format(ev=event)
            except Exception as exc:
                retval.append((lineindex, -1,
                               CONFIG['destination_pipeline_queue'], repr(exc)))
                line_valid = False
            if line_valid:
                lines_valid += 1
    retval = {"total": lineindex+1,
              "lines_invalid": lineindex+1-lines_valid,
              "errors": retval}
    return create_response(retval)


@app.route('/classification/types')
def classification_types():
    return create_response(TAXONOMY)


@app.route('/harmonization/event/fields')
def harmonization_event_fields():
    return create_response(EVENT_FIELDS['event'])


@app.route('/submit', methods=['POST'])
def submit():
    parameters = handle_parameters(request.form)
    tmp_file = get_temp_file()
    if not tmp_file:
        return create_response('No file')

    destination_pipeline = PipelineFactory.create(PipelineParameters(),
                                                  logger=app.logger,
                                                  direction='destination')
    if not CONFIG.get('destination_pipeline_queue_formatted', False):
        destination_pipeline.set_queues(CONFIG['destination_pipeline_queue'], "destination")
        destination_pipeline.connect()

    time_observation = DateTime().generate_datetime_now()

    successful_lines = 0

    raw_header = []
    with open(tmp_file[0], encoding='utf8') as handle:
        handle_rewindable = RewindableFileHandle(handle)
        reader = csv.reader(handle_rewindable, delimiter=parameters['delimiter'],
                            quotechar=parameters['quotechar'],
                            skipinitialspace=parameters['skipInitialSpace'],
                            escapechar=parameters['escapechar'],
                            )
        if parameters['has_header']:
            next(reader)
            raw_header.append(handle_rewindable.current_line)
        for _ in range(parameters['skipInitialLines']):
            next(reader)
        for lineindex, line in enumerate(reader):
            event = Event()
            try:
                for columnindex, (column, value) in \
                        enumerate(zip(parameters['columns'], line)):
                    if not column or not value:
                        continue
                    if column.startswith('time.'):
                        parsed = dateutil.parser.parse(value, fuzzy=True)
                        if not parsed.tzinfo:
                            value += parameters['timezone']
                            parsed = dateutil.parser.parse(value)
                        value = parsed.isoformat()
                    if column == 'extra':
                        value = handle_extra(value)
                    event.add(column, value)
                for key, value in parameters.get('constant_fields', {}).items():
                    if key not in event:
                        event.add(key, value)
                for key, value in request.form.items():
                    if not key.startswith('custom_'):
                        continue
                    key = key[7:]
                    if key not in event:
                        event.add(key, value)
                if CONFIG.get('destination_pipeline_queue_formatted', False):
                    queue_name = CONFIG['destination_pipeline_queue'].format(ev=event)
                    destination_pipeline.set_queues(queue_name, "destination")
                    destination_pipeline.connect()
            except Exception:
                app.logger.exception('Failure')
                continue
            if 'classification.type' not in event:
                event.add('classification.type', parameters['classification.type'])
            if 'classification.identifier' not in event:
                event.add('classification.identifier', parameters['classification.identifier'])
            if 'feed.code' not in event:
                event.add('feed.code', parameters['feed.code'])
            if 'time.observation' not in event:
                event.add('time.observation', time_observation, sanitize=False)
            if 'raw' not in event:
                event.add('raw', ''.join(raw_header + [handle_rewindable.current_line]))
            raw_message = MessageFactory.serialize(event)
            destination_pipeline.send(raw_message)
            successful_lines += 1
    return create_response('Successfully processed %s lines.' % successful_lines)


@app.route('/uploads/current')
def get_current_upload():
    filename, _ = get_temp_file()
    with open(filename, encoding='utf8') as handle:
        resp = create_response(handle.read(), content_type='text/csv')
    return resp


def main():
    app.run()


if __name__ == "__main__":
    main()
