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
    'use_header': False,  # TODO: define how it should be used
    'quotechar': '"',
    'columns': [],
    'ignore': [],
    'dryrun': True,
    }


app = Flask('intelmq-webinput-csv')


with open(HARMONIZATION_CONF_FILE) as handle:
    EVENT_FIELDS = json.load(handle)


with open('/opt/intelmq/etc/webinput_csv.conf') as handle:
    CONFIG = json.load(handle)


class Parameters(object):
    pass


@app.route('/')
def form():
    return('''<html><body>
    <form action="/upload" method="POST" enctype="multipart/form-data">
    <input type="file" name="file">
    <input type="text" name="text">
    <input type="submit" value="Submit">
    </form></body></html>
    ''')


@app.route('/upload', methods=['POST'])
def upload_file():
    success = False
    if request.method == 'POST':
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
    if success == True:
        TEMPORARY_FILES.append((filedescriptor, filename))
        preview = []
        with open(filename) as handle:
            for counter in range(CONFIG.get('preview_lines', 1000)):
                line = handle.readline()
                if line:
                    preview.append(line)
        response = make_response(jsonify(preview))
        response.mimetype = 'application/json'
        response.headers['Content-Type'] = "text/json; charset=utf-8"
        response.headers['Access-Control-Allow-Origin'] = "*"
        return response
    else:
        response = make_response('no file or text')
        response.mimetype = 'application/json'
        response.headers['Content-Type'] = "text/json; charset=utf-8"
        response.headers['Access-Control-Allow-Origin'] = "*"
        return response


@app.route('/preview', methods=['GET', 'POST'])
def preview():
    if request.method == 'POST':
        parameters = {}
        for key, default_value in PARAMETERS.items():
            parameters[key] = request.form.get(key, default_value)
        if parameters['dryrun']:
            parameters['classification.type'] = 'test'
            parameters['classification.identifier'] = 'test'
        retval = jsonify(parameters)
        if not TEMPORARY_FILES:
            return jsonify('No file')
        if type(parameters['columns']) is not list:
            parameters['columns'] = parameters['columns'].split(',')
            parameters['ignore'] = [bool(int(a)) for a in parameters['ignore'].split(',')]
        columns = [a if not b else None for a, b in zip(parameters['columns'], parameters['ignore'])]
        retval = []
        event = Event()
        with open(TEMPORARY_FILES[-1][1]) as handle:
            reader = csv.reader(handle, delimiter=parameters['delimiter'],
                                quotechar=parameters['quotechar'])
            if parameters['has_header']:
                next(reader)
            for lineindex, line in enumerate(reader):
                for columnindex, (column, value) in enumerate(zip(columns, line)):
                    if not column:
                        continue
                    if column.startswith('time.') and '+' not in value:
                        value += parameters['timezone']
                    value = event._Message__sanitize_value(column, value)
                    valid = event._Message__is_valid_value(column, value)
                    if not valid[0]:
                        retval.append((lineindex, columnindex, value, valid[1]))
            retval = {"total": lineindex+1, "errors": retval}
            response = make_response(jsonify(retval))
            response.mimetype = 'application/json'
            response.headers['Content-Type'] = "text/json; charset=utf-8"
            response.headers['Access-Control-Allow-Origin'] = "*"
            return response
    else:
        retval = '''<html><body>
    <form action="/preview" method="POST" enctype="multipart/form-data">'''
        for key, default_value in PARAMETERS.items():
            retval += '{key}: <input type="text" name="{key}" value="{value}"><br />'.format(key=key, value=default_value)
        retval += '''<input type="submit" value="Submit">
        </form></body></html>
        '''
    return retval


@app.route('/classification/types')
def classification_types():
    response = make_response(jsonify(ClassificationType.allowed_values))
    response.mimetype = 'application/json'
    response.headers['Content-Type'] = "text/json; charset=utf-8"
    response.headers['Access-Control-Allow-Origin'] = "*"
    return response


@app.route('/harmonization/event/fields')
def harmonization_event_fields():
    response = make_response(jsonify(EVENT_FIELDS['event']))
    response.mimetype = 'application/json'
    response.headers['Content-Type'] = "text/json; charset=utf-8"
    response.headers['Access-Control-Allow-Origin'] = "*"
    return response


@app.route('/submit', methods=['POST'])
def submit():
    parameters = {}
    for key, default_value in PARAMETERS.items():
        parameters[key] = request.form.get(key, default_value)
    if parameters['dryrun']:
        parameters['classification.type'] = 'test'
        parameters['classification.identifier'] = 'test'
    retval = jsonify(parameters)
    if not TEMPORARY_FILES:
        return jsonify('No file')
    if type(parameters['columns']) is not list:
        parameters['columns'] = parameters['columns'].split(',')
        parameters['ignore'] = [bool(int(a)) for a in parameters['ignore'].split(',')]
    columns = [a if not b else None for a, b in zip(parameters['columns'], parameters['ignore'])]

    pipelineparameters = Parameters
    destination_pipeline = PipelineFactory.create(pipelineparameters)
    destination_pipeline.set_queues(CONFIG['destination_pipeline'], "destination")
    destination_pipeline.connect()

    with open(TEMPORARY_FILES[-1][1]) as handle:
        reader = csv.reader(handle, delimiter=parameters['delimiter'],
                            quotechar=parameters['quotechar'])
        if parameters['has_header']:
            next(reader)
        for lineindex, line in enumerate(reader):
            event = Event()
            for columnindex, (column, value) in enumerate(zip(columns, line)):
                if not column:
                    continue
                if column.startswith('time.') and '+' not in value:
                    value += parameters['timezone']
                event.add(column, value)
            if 'classification.type' not in event:
                event.add('classification.type', parameters['classification.type'])
            if 'classification.identifier' not in event:
                event.add('classification.identifier', parameters['classification.identifier'])
            raw_message = MessageFactory.serialize(event)
            destination_pipeline.send(raw_message)
    return 'success'


def delete_temporary_files():
    for filedescriptor, filename in TEMPORARY_FILES:
        os.remove(filename)


def main():
    atexit.register(delete_temporary_files)
    app.run()


if __name__ == "__main__":
    main()
