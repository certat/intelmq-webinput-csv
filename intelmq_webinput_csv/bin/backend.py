# -*- coding: utf-8 -*-
from flask import Flask, request
import tempfile
import os
import atexit


TEMPORARY_FILES = []


app = Flask('intelmq-webinput-csv')


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
    if request.method == 'POST':
        if 'file' in request.files and request.files['file'].filename:
            file = request.files['file']
            filedescriptor, filename = tempfile.mkstemp(suffix=".csv", text=True)
            TEMPORARY_FILES.append((filedescriptor, filename))
            file.save(filename)
        elif 'text' in request.form and request.form['text']:
            filedescriptor, filename = tempfile.mkstemp(suffix=".csv", text=True)
            TEMPORARY_FILES.append((filedescriptor, filename))
            with os.fdopen(filedescriptor, mode='w') as handle:
                handle.write(request.form['text'])
    return('')


def delete_temporary_files():
    for filedescriptor, filename in TEMPORARY_FILES:
        os.remove(filename)


def main():
    atexit.register(delete_temporary_files)
    app.run()


if __name__ == "__main__":
    main()
