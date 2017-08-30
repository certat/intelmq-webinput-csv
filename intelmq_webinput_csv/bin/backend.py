# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, make_response
import tempfile
import os
import atexit
from intelmq.lib.harmonization import ClassificationType
from intelmq.lib.message import Event
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
            for counter in range(100):
                line = handle.readline()
                if line:
                    preview.append(line)
        response = make_response(jsonify(preview))
        response.mimetype = 'application/json'
        response.headers['Content-Type'] = "text/json; charset=utf-8"
        response.headers['Access-Control-Allow-Origin'] = "*"
        return response
    return ''


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
                if lineindex == 100:
                    break
                for columnindex, (column, value) in enumerate(zip(columns, line)):
                    if not column:
                        continue
                    value = event._Message__sanitize_value(column, value)
                    valid = event._Message__is_valid_value(column, value)
                    if not valid[0]:
                        retval.append((lineindex+1, columnindex+1, value, valid[1]))
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


def delete_temporary_files():
    for filedescriptor, filename in TEMPORARY_FILES:
        os.remove(filename)


def main():
    atexit.register(delete_temporary_files)
    app.run()


if __name__ == "__main__":
    main()
