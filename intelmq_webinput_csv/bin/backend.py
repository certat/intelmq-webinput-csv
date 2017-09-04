# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, make_response
import tempfile
import os
import atexit
from intelmq.lib.harmonization import ClassificationType
from intelmq.lib.message import Event, MessageFactory
from intelmq.lib.pipeline import PipelineFactory
from intelmq import HARMONIZATION_CONF_FILE
import json
import csv


TEMPORARY_FILES = []
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


app = Flask('intelmq-webinput-csv')


with open(HARMONIZATION_CONF_FILE) as handle:
    EVENT_FIELDS = json.load(handle)


with open('/opt/intelmq/etc/webinput_csv.conf') as handle:
    CONFIG = json.load(handle)


class Parameters(object):
    pass


def handle_parameters(form):
    parameters = {}
    for key, default_value in CONFIG.items():
        parameters[key] = form.get(key, default_value)
    for key, default_value in PARAMETERS.items():
        parameters[key] = form.get(key, default_value)
    if parameters['dryrun']:
        parameters['classification.type'] = 'test'
        parameters['classification.identifier'] = 'test'
    if type(parameters['columns']) is not list:  # for debugging purpose only
        parameters['use_column'] = [json.loads(a.lower()) for a in
                                    parameters['use_column'].split(',')]
        parameters['columns'] = parameters['columns'].split(',')
    parameters['columns'] = [a if b else None for a, b in
                             zip(parameters['columns'],
                                 parameters['use_column'])]
    # for debugging purpose only
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
    return('''<html><body>
    <form action="/upload" method="POST" enctype="multipart/form-data">
    <input type="file" name="file">
    <input type="text" name="text">
    <input type="submit" value="Submit">
    </form></body></html>
    ''')


@app.route('/form/<kind>')
def preview_form(kind):
    retval = '''<html><body>
<form action="/%s" method="POST" enctype="multipart/form-data">''' % kind
    for key, default_value in sorted(PARAMETERS.items()):
        retval += '{key}: <input type="text" name="{key}" value="{value}"><br />'.format(key=key, value=default_value)
    retval += '''<input type="submit" value="Submit">
</form></body></html>
'''
    return retval


@app.route('/upload', methods=['POST'])
def upload_file():
    success = False
    print('files:', list(request.files.keys()))
    print('form data:', list(request.form.keys()))
    if 'file' in request.files and request.files['file'].filename:
        filedescriptor, filename = tempfile.mkstemp(suffix=".csv", text=True)
        request.files['file'].save(filename)
        success = True
    elif 'text' in request.form and request.form['text']:
        filedescriptor, filename = tempfile.mkstemp(suffix=".csv", text=True)
        with os.fdopen(filedescriptor, mode='w') as handle:
            handle.write(request.form['text'])
        success = True
    if success:
        TEMPORARY_FILES.append((filedescriptor, filename))
        parameters = handle_parameters(request.form)
        preview = []
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
                preview.append(line)
        return create_response(preview)
    else:
        return create_response('no file or text')


@app.route('/preview', methods=['POST'])
def preview():
    parameters = handle_parameters(request.form)
    if not TEMPORARY_FILES:
        app.logger.info('no file')
        return create_response('No file')
    retval = []
    lines_valid = 0
    event = Event()
    with open(TEMPORARY_FILES[-1][1]) as handle:
        reader = csv.reader(handle, delimiter=parameters['delimiter'],
                            quotechar=parameters['quotechar'])
        if parameters['has_header']:
            next(reader)
        for _ in range(parameters['skipInitialLines']):
            next(reader)
        for lineindex, line in enumerate(reader):
            line_valid = True
            for columnindex, (column, value) in \
                    enumerate(zip(parameters['columns'], line)):
                if not column:
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
    if not TEMPORARY_FILES:
        return create_response('No file')

    pipelineparameters = Parameters
    destination_pipeline = PipelineFactory.create(pipelineparameters)
    destination_pipeline.set_queues(CONFIG['destination_pipeline'], "destination")
    destination_pipeline.connect()

    successful_lines = 0

    with open(TEMPORARY_FILES[-1][1]) as handle:
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
                    if not column:
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
    return create_response({'successful_lines': successful_lines})


def delete_temporary_files():
    for filedescriptor, filename in TEMPORARY_FILES:
        os.remove(filename)


def main():
    atexit.register(delete_temporary_files)
    app.run()


if __name__ == "__main__":
    main()
