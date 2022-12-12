# -*- coding: utf-8 -*-
# Copyright (c) 2017-2018 nic.at GmbH <wagner@cert.at>
# SPDX-License-Identifier: AGPL-3.0
import traceback
import os

from werkzeug.middleware.proxy_fix import ProxyFix
from flask import Flask, request, render_template

from intelmq import CONFIG_DIR
from intelmq.lib.harmonization import DateTime, IPAddress
from intelmq.bots.experts.taxonomy.expert import TAXONOMY
from intelmq.lib.message import MessageFactory
from intelmq.lib.pipeline import PipelineFactory

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

    return app


app = create_app()


@app.route('/')
def form():
    return render_template('upload.html')


@app.route('/upload', methods=['POST'])
def upload_file():
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


@app.route('/preview', methods=['GET', 'POST'])
def preview():
    if request.method == 'GET':
        return render_template('preview.html')

    parameters = util.handle_parameters(request.form)
    tmp_file = util.get_temp_file()
    if not tmp_file.exists():
        app.logger.info('no file')
        return util.create_response('No file')

    exceptions = []
    invalid_lines = []

    with CSV.create(file=tmp_file, **parameters) as reader:
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

    # Save invalid lines to CSV file in tmp
    util.save_failed_csv(reader, invalid_lines)

    return {
        "total": len(reader),
        "lines_invalid": len(invalid_lines),
        "errors": exceptions
    }


@app.route('/classification/types')
def classification_types():
    return TAXONOMY


@app.route('/harmonization/event/fields')
def harmonization_event_fields():
    events = util.load_harmonization_config(load_json=True)
    return events['event']


@app.route('/submit', methods=['POST'])
def submit():
    tmp_file = util.get_temp_file()
    parameters = util.handle_parameters(request.form)
    if not tmp_file.exists():
        return util.create_response('No file')

    destination_pipeline = PipelineFactory.create(pipeline_args=app.config['INTELMQ'],
                                                  logger=app.logger,
                                                  direction='destination')
    if not app.config.get('DESTINATION_PIPELINE_QUEUE_FORMATTED', False):
        destination_pipeline.set_queues(app.config['DESTINATION_PIPELINE_QUEUE'], "destination")
        destination_pipeline.connect()

    successful_lines = 0
    invalid_lines = []
    parameters['time_observation'] = DateTime().generate_datetime_now()

    with CSV.create(tmp_file, **parameters) as reader:
        for line in reader:
            try:
                event = line.parse()

                if app.config.get('DESTINATION_PIPELINE_QUEUE_FORMATTED', False):
                    queue_name = app.config['DESTINATION_PIPELINE_QUEUE'].format(ev=event)
                    destination_pipeline.set_queues(queue_name, "destination")
                    destination_pipeline.connect()

                raw_message = MessageFactory.serialize(event)
                destination_pipeline.send(raw_message)

            except InvalidCellException as ice:
                app.logger.warning(ice.message)
                invalid_lines.append(line)
            except Exception as e:
                app.logger.error(f"Unknown error occured: {e}")
            else:
                successful_lines += 1

    # Save invalid lines to CSV file in tmp
    util.save_failed_csv(reader, invalid_lines)

    return {
        "successful_lines": len(reader),
        "lines_invalid": len(invalid_lines),
    }


@app.route('/uploads/current')
def get_current_upload():
    tmp_file = util.get_temp_file()
    with tmp_file.open(encoding='utf8') as handle:
        resp = util.create_response(handle.read(), content_type='text/csv')
    return resp


@app.route('/uploads/failed')
def get_failed_upload():
    tmp_file = util.get_temp_file(filename='webinput_invalid_csv.csv')

    if not tmp_file.exists():
        return "File not found", 404

    with tmp_file.open(encoding='utf8') as handle:
        resp = util.create_response(handle.read(), content_type='text/csv')
    return resp


def main():
    app.run()


if __name__ == "__main__":
    main()
