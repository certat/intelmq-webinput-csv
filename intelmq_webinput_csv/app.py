# -*- coding: utf-8 -*-
# Copyright (c) 2017-2018 nic.at GmbH <wagner@cert.at>
# SPDX-License-Identifier: AGPL-3.0
import traceback
import os

from flask_socketio import SocketIO, emit
from flask import Flask, request, render_template, send_file

from intelmq import CONFIG_DIR
from intelmq.lib.harmonization import DateTime, IPAddress
from intelmq.bots.experts.taxonomy.expert import TAXONOMY
from intelmq.lib.message import MessageFactory

from intelmq_webinput_csv.lib import util
from intelmq_webinput_csv.lib.exceptions import InvalidCellException
from intelmq_webinput_csv.lib.csv import CSV


def create_app():
    """ Function for create Flask app object

    Returns:
        app: object
    """
    # Start Flask App
    app = Flask('intelmq_webinput_csv')
    app.config.from_prefixed_env()

    # Load IntelMQ-Webinput-CSV specific config
    config_path = app.config.get('INTELMQ_WEBINPUT_CONFIG', os.path.join(CONFIG_DIR, 'webinput_csv.conf'))
    app.config.from_file(config_path, load=util.load_config)

    socketio = SocketIO(app, always_connect=True)

    return (app, socketio)


app, socketio = create_app()


@app.route('/')
def form():
    return render_template('upload.html')


@app.route('/upload', methods=['POST'])
def upload():
    tmp_file = util.get_temp_file()

    if 'file' in request.files and request.files['file'].filename:
        request.files['file'].save(tmp_file)
    elif 'text' in request.form and request.form['text']:
        with tmp_file.open(mode='w', encoding='utf8') as handle:
            handle.write(request.form['text'])
    elif request.form.get('use_last_file') and not tmp_file.exists():
        return util.create_response('no file or text')

    parameters = util.handle_parameters(request.form)
    preview = []
    valid_ip_addresses = None
    valid_date_times = None

    try:
        with CSV.create(file=tmp_file, **parameters) as reader:
            total_lines = len(reader)

            # If has columns, set first line as column
            if parameters.get('has_header', False):
                preview.append(reader.columns)

            for line in reader:

                if valid_ip_addresses is None:  # first data line
                    valid_ip_addresses = [0] * len(line)
                    valid_date_times = [0] * len(line)
                for columnindex, value in enumerate(line):
                    if IPAddress.is_valid(value):
                        valid_ip_addresses[columnindex] += 1
                    if DateTime.is_valid(value):
                        valid_date_times[columnindex] += 1
                preview.append(line.cells)
    except Exception:
        preview = [['Parse Error'], ['Is the number of columns consistent?']] + \
            [[x] for x in traceback.format_exc().splitlines()] + \
            [['Current line (%d):' % line.index]] + \
            [line]
    column_types = ["IPAddress" if x / (total_lines if total_lines else 1) > 0.7 else None for x in valid_ip_addresses]
    column_types = ["DateTime" if valid_date_times[i] / (total_lines if total_lines else 1) > 0.7 else x for i, x in enumerate(column_types)]
    return {
        "column_types": column_types,
        "use_column": [bool(x) for x in column_types],
        "preview": preview,
    }


@app.route('/preview', methods=['GET'])
def preview():
    if request.method == 'GET':
        # Check config for generating UUID
        uuid = util.generate_uuid() if app.config.get('GENERATE_UUID') else ''
        return render_template('preview.html', uuid=uuid)


@socketio.on('validate', namespace='/preview')
def validate(data):
    parameters = util.handle_parameters(data)
    tmp_file = util.get_temp_file()

    if not tmp_file.exists():
        app.logger.info('no file')
        emit("finished", {'message': 'no file found'})
        return

    exceptions = []
    invalid_lines = []

    with CSV.create(file=tmp_file, **parameters) as reader:
        segment_size = util.calculate_segments(reader)

        for line in reader:

            try:
                event, invalids = line.validate()

                if invalids:
                    invalid_lines.append(line)

                if app.config.get('DESTINATION_PIPELINE_QUEUE_FORMATTED', False):
                    app.config['DESTINATION_PIPELINE_QUEUE'].format(ev=event)

                for invalid in invalids:
                    exceptions.append((
                        invalid.line_index,
                        invalid.column_index,
                        invalid.key,
                        repr(invalid)
                    ))

            except Exception as exc:
                exceptions.append((
                    line.index,
                    -1,
                    app.config['DESTINATION_PIPELINE_QUEUE'],
                    repr(exc)
                ))

            if (line.index % segment_size) == 0:
                emit('processing', {
                    "total": len(reader),
                    "failed": invalid_lines,
                    "successful": line.index - invalid_lines,
                    "progress": round((len(reader) / line.index) * 100)
                })

    # Save invalid lines to CSV file in tmp
    util.save_failed_csv(reader, invalid_lines)

    emit('finished', {
        "total": len(reader),
        "lines_invalid": invalid_lines,
        "errors": exceptions
    })


@app.route('/classification/types')
def classification_types():
    return TAXONOMY


@app.route('/harmonization/event/fields')
def harmonization_event_fields():
    events = util.load_harmonization_config(load_json=True)
    return events['event']


@socketio.on('submit', namespace='/preview')
def submit(data):
    tmp_file = util.get_temp_file()
    parameters = util.handle_parameters(data)
    parameters['loadLinesMax'] = 0

    if not tmp_file.exists():
        return util.create_response('No file')

    successful_lines = 0
    invalid_lines = []
    parameters['time_observation'] = DateTime().generate_datetime_now()

    with CSV.create(tmp_file, **parameters) as reader:
        segment_size = util.calculate_segments(reader)

        for line in reader:
            try:
                event = line.parse()

                destination_pipeline = util.create_pipeline(parameters.get('pipeline'), event=event)
                raw_message = MessageFactory.serialize(event)
                destination_pipeline.send(raw_message)

            except InvalidCellException as ice:
                app.logger.warning(ice.message)
                invalid_lines.append(line)
            except Exception as e:
                app.logger.error(f"Unknown error occured: {e}")
            else:
                successful_lines += 1

            if (line.index % segment_size) == 0:
                data = {
                    "total": len(reader),
                    "successful": successful_lines,
                    "failed": line.index - successful_lines,
                    "progress": round((line.index + 1) / len(reader) * 100)
                }
                emit('processing', data, namespace="/preview")

    # Save invalid lines to CSV file in tmp
    util.save_failed_csv(reader, invalid_lines)

    emit('finished', {
        'total': len(reader),
        'successful': successful_lines,
        "successful_lines": len(reader),
        "lines_invalid": len(invalid_lines),
    }, namespace="/preview")


@app.route('/uploads/current')
def get_current_upload():
    tmp_file = util.get_temp_file()

    if not tmp_file.exists():
        return "File not found", 404

    return send_file(tmp_file, mimetype='text/csv')


@app.route('/uploads/failed')
def get_failed_upload():
    tmp_file = util.get_temp_file(filename='webinput_invalid_csv.csv')

    if not tmp_file.exists():
        return "File not found", 404

    return send_file(tmp_file, mimetype='text/csv')


def main():
    socketio.run(app)


if __name__ == "__main__":
    main()
