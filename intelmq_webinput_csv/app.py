# -*- coding: utf-8 -*-
# Copyright (c) 2017-2018 nic.at GmbH <wagner@cert.at>
# SPDX-License-Identifier: AGPL-3.0
import traceback
import os
import secrets

from flask_socketio import SocketIO, emit
from werkzeug.middleware.proxy_fix import ProxyFix
from flask import Flask, request, render_template, send_file, session, flash, redirect

from intelmq import CONFIG_DIR
from intelmq.lib.harmonization import DateTime, IPAddress
from intelmq.bots.experts.taxonomy.expert import TAXONOMY
from intelmq.lib.message import MessageFactory

from intelmq_webinput_csv.lib import util
from intelmq_webinput_csv.lib.decorators import use_csv_file
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

    # Use ProxyFix if configured
    if app.config.get("USE_PROXY_FIX"):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_prefix=1, x_for=1, x_host=1)

    # Ensure a secret_key is set; not used for storing long data so can be reset during restarts
    if not app.config.get("SECRET_KEY"):
        app.config['SECRET_KEY'] = secrets.token_hex(32)

    cors_origins = app.config.get("CORS_ALLOWED_ORIGINS")
    socketio = SocketIO(app, always_connect=True, cors_allowed_origins=cors_origins)

    return (app, socketio)


# Create Flask App
app, socketio = create_app()


@app.route('/')
def form():
    if not session.get('prefix'):
        session['prefix'] = secrets.token_hex(8)
        session.permanent = True

    return render_template('upload.html')


@app.route('/upload', methods=['POST'])
@use_csv_file()
def upload_file(csv_file):
    if 'file' in request.files and request.files['file'].filename:
        request.files['file'].save(csv_file)
    elif 'text' in request.form and request.form['text']:
        with csv_file.open(mode='w', encoding='utf8') as handle:
            handle.write(request.form['text'])
    elif request.form.get('use_last_file') and not csv_file.exists():
        flash("File not found!", "error")
        return redirect('/')

    parameters = util.handle_parameters(request.form)
    preview = []
    valid_ip_addresses = None
    valid_date_times = None

    try:
        with CSV.create(file=csv_file, **parameters) as reader:
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


@app.route('/preview')
@use_csv_file(required=True)
def preview(_):
    # Check config for generating UUID
    uuid = util.generate_uuid() if app.config.get('GENERATE_UUID') else ''
    return render_template('preview.html', uuid=uuid)


@socketio.on('validate', namespace='/preview')
@use_csv_file(required=True)
def validate(csv_file, data):
    parameters = util.handle_parameters(data)
    exceptions = []
    invalid_lines = []

    with CSV.create(file=csv_file, **parameters) as reader:
        total_lines = min(len(reader), reader.max_lines)
        segment_size = util.calculate_segments(len(reader))

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
                    "total": total_lines,
                    "failed": len(invalid_lines),
                    "successful": (line.index + 1) - len(invalid_lines),
                    "progress": round((line.index + 1) / total_lines * 100)
                })

    # Save invalid lines to CSV file in tmp
    util.save_failed_csv(reader, invalid_lines, session=session)

    emit('finished', {
        "total": total_lines,
        "successful": total_lines - len(invalid_lines),
        "failed": len(invalid_lines),
        "errors": exceptions,
        "message": "Validation finished!"
    })


@app.route('/classification/types')
def classification_types():
    return TAXONOMY


@app.route('/harmonization/event/fields')
def harmonization_event_fields():
    events = util.load_harmonization_config(load_json=True)
    return events['event']


@socketio.on('submit', namespace='/preview')
@use_csv_file(required=True)
def submit(csv_file, data):
    parameters = util.handle_parameters(data)
    parameters['loadLinesMax'] = 0

    successful_lines = 0
    invalid_lines = []
    parameters['time_observation'] = DateTime().generate_datetime_now()

    with CSV.create(csv_file, **parameters) as reader:
        segment_size = util.calculate_segments(len(reader))

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
                invalid_lines.append(line)
                app.logger.error(f"Unknown error occured: {e}")
            else:
                successful_lines += 1

            if (line.index % segment_size) == 0:
                data = {
                    "total": len(reader),
                    "successful": successful_lines,
                    "failed": len(invalid_lines),
                    "progress": round((line.index + 1) / len(reader) * 100)
                }
                emit('processing', data, namespace="/preview")

    # Save invalid lines to CSV file in tmp
    util.save_failed_csv(reader, invalid_lines, session=session)

    emit('finished', {
        'total': len(reader),
        'successful': successful_lines,
        "failed": len(invalid_lines),
        'message': f'Successfully processed {successful_lines} lines.'
    }, namespace="/preview")


@app.route('/uploads/current')
@use_csv_file(required=True)
def get_current_upload(csv_file):
    return send_file(csv_file, mimetype='text/csv')


@app.route('/uploads/failed')
@use_csv_file(filename='webinput_invalid', required=True)
def get_failed_upload(csv_file):
    return send_file(csv_file, mimetype='text/csv')


def main():
    socketio.run(app)


if __name__ == "__main__":
    main()
