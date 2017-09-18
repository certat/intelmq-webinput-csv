# -*- coding: utf-8 -*-
import codecs
import csv
import json
import os
import pickle
import tempfile
import urllib.parse

import pkg_resources
from flask import Flask, jsonify, make_response, request, send_from_directory

from intelmq import HARMONIZATION_CONF_FILE
from intelmq.lib.harmonization import ClassificationType, IPAddress
from intelmq.lib.message import Event, MessageFactory
from intelmq.lib.pipeline import PipelineFactory

with open('/opt/intelmq/etc/webinput_csv.conf') as handle:
    CONFIG = json.load(handle)
    BASE_URL = CONFIG.get('base_url', '')
    if BASE_URL.endswith('/'):
        BASE_URL = BASE_URL[:-1]


PARAMETERS = {
    'timezone': '+00:00',
    'classification.type': 'test',
    'classification.identifier': 'test',
    'text': 'default',
    'delimiter': ',',
    'has_header': False,
    'quotechar': '\"',
    'escapechar': '\\',
    'columns': [],
    'use_column': [],
    'dryrun': True,
    'skipInitialSpace': False,
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
    with codecs.open(filename, encoding='utf8') as handle:
        STATIC_FILES[static_file] = handle.read()
        if static_file.startswith('js/'):
            STATIC_FILES[static_file] = STATIC_FILES[static_file].replace('__BASE_URL__', BASE_URL)


app = Flask('intelmq_webinput_csv')


with open(HARMONIZATION_CONF_FILE) as handle:
    EVENT_FIELDS = json.load(handle)


class Parameters(object):
    pass


def write_temp_file(data):
    with open('/opt/intelmq/var/lib/webinput_csv.temp', 'wb') as handle:
        pickle.dump(data, handle)


def get_temp_file():
    with open('/opt/intelmq/var/lib/webinput_csv.temp', 'rb') as handle:
        return pickle.load(handle)


def handle_parameters(form):
    parameters = {}
    for key, default_value in CONFIG.items():
        parameters[key] = form.get(key, default_value)
    for key, default_value in PARAMETERS.items():
        parameters[key] = form.get(key, default_value)
    if parameters['dryrun']:
        parameters['classification.type'] = 'test'
        parameters['classification.identifier'] = 'test'
    if type(parameters['columns']) is not list:
        parameters['use_column'] = [json.loads(a.lower()) for a in
                                    parameters['use_column'].split(',')]
        parameters['columns'] = parameters['columns'].split(',')
    parameters['columns'] = [a if b else None for a, b in
                             zip(parameters['columns'],
                                 parameters['use_column'])]
    parameters['skipInitialLines'] = int(parameters['skipInitialLines'])
    parameters['loadLinesMax'] = int(parameters['loadLinesMax'])
    return parameters


def create_response(text):
    is_json = False
    if type(text) is not str:
        text = jsonify(text)
        is_json = True
    response = make_response(text)
    if is_json:
        response.mimetype = 'application/json'
        response.headers['Content-Type'] = "text/json; charset=utf-8"
    response.headers['Access-Control-Allow-Origin'] = "*"
    return response


@app.route('/')
def form():
    response = make_response(STATIC_FILES['index.html'])
    response.mimetype = 'text/html'
    response.headers['Content-Type'] = "text/html; charset=utf-8"
    return response


@app.route('/plugins/<path:page>')
def plugins(page):
    return send_from_directory('static/plugins', page)


@app.route('/js/<page>')
def js(page):
    response = make_response(STATIC_FILES['js/%s' % page])
    response.mimetype = 'application/x-javascript'
    response.headers['Content-Type'] = "application/x-javascript; charset=utf-8"
    return response


@app.route('/upload', methods=['POST'])
def upload_file():
    success = False
    if 'file' in request.files and request.files['file'].filename:
        filedescriptor, filename = tempfile.mkstemp(suffix=".csv", text=True)
        request.files['file'].save(filename)
        request.files['file'].stream.seek(0)
        total_lines = request.files['file'].stream.read().count(b'\n')  # we don't care about headers here
        success = True
    elif 'text' in request.form and request.form['text']:
        filedescriptor, filename = tempfile.mkstemp(suffix=".csv", text=True)
        with os.fdopen(filedescriptor, mode='w') as handle:
            handle.write(request.form['text'])
        success = True
        total_lines = request.form['text'].count('\n')
    if not success and request.form.get('use_last_file', False):
        success = True
        filedescriptor, filename, total_lines = get_temp_file()
    elif success:
        write_temp_file((filedescriptor, filename, total_lines))
    if not success:
        return create_response('no file or text')

    parameters = handle_parameters(request.form)
    preview = []
    valid_ip_addresses = None
    with open(filename) as handle:
        reader = csv.reader(handle, delimiter=parameters['delimiter'],
                            quotechar=parameters['quotechar'],
                            skipinitialspace=parameters['skipInitialSpace'],
                            escapechar=parameters['escapechar'],
                            )
        for lineindex, line in enumerate(reader):
            if parameters['skipInitialLines']:
                if parameters['has_header'] and lineindex == 1:
                    for _ in range(parameters['skipInitialLines']):
                        next(reader)
                elif not parameters['has_header'] and lineindex == 0:
                    for _ in range(parameters['skipInitialLines']):
                        next(reader)
            if lineindex >= parameters['loadLinesMax']:
                break
            if valid_ip_addresses is None:
                valid_ip_addresses = [0] * len(line)
            for columnindex, value in enumerate(line):
                if IPAddress.is_valid(value, sanitize=True):
                    valid_ip_addresses[columnindex] += 1
            preview.append(line)
    column_types = ["IPAddress" if x/total_lines > 0.7 else None for x in valid_ip_addresses]
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
    event = Event()
    with open(tmp_file[1]) as handle:
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
            line_valid = True
            for columnindex, (column, value) in \
                    enumerate(zip(parameters['columns'], line)):
                if not column or not value:
                    continue
                if column.startswith('time.') and '+' not in value:
                    value += parameters['timezone']
                sanitized = event._Message__sanitize_value(column, value)
                valid = event._Message__is_valid_value(column, sanitized)
                if not valid[0]:
                    retval.append((lineindex, columnindex, value, valid[1]))
                    line_valid = False
            if line_valid:
                lines_valid += 1
    retval = {"total": lineindex+1,
              "lines_invalid": lineindex+1-lines_valid,
              "errors": retval}
    return create_response(retval)


@app.route('/classification/types')
def classification_types():
    return create_response(ClassificationType.allowed_values)


@app.route('/harmonization/event/fields')
def harmonization_event_fields():
    return create_response(EVENT_FIELDS['event'])


@app.route('/submit', methods=['POST'])
def submit():
    parameters = handle_parameters(request.form)
    temp_file = get_temp_file()
    if not temp_file:
        return create_response('No file')

    pipelineparameters = Parameters
    destination_pipeline = PipelineFactory.create(pipelineparameters)
    destination_pipeline.set_queues(CONFIG['destination_pipeline'], "destination")
    destination_pipeline.connect()

    successful_lines = 0

    with open(temp_file[1]) as handle:
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
            try:
                for columnindex, (column, value) in \
                        enumerate(zip(parameters['columns'], line)):
                    if not column or not value:
                        continue
                    if column.startswith('time.') and '+' not in value:
                        value += parameters['timezone']
                    event.add(column, value)
            except Exception:
                continue
            if 'classification.type' not in event:
                event.add('classification.type', parameters['classification.type'])
            if 'classification.identifier' not in event:
                event.add('classification.identifier', parameters['classification.identifier'])
            raw_message = MessageFactory.serialize(event)
            destination_pipeline.send(raw_message)
            successful_lines += 1
    return create_response('Successfully processed %s lines.' % successful_lines)


def main():
    app.run()


if __name__ == "__main__":
    main()
