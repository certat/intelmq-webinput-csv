from typing import Optional
from functools import wraps

from flask import session, redirect, flash

from intelmq_webinput_csv.lib import util


def use_csv_file(filename: Optional[str]=None, required: bool=False):
    """ Decorator for creating reference to CSV file in Flask functions

    The majority of Flask web functions require a reference to a temp file used to
    read/write the CSV file from. Certain functions requires a existing file and some
    will create it. This decorator ensures that for functions using this decorator that
    a CSV file reference is created based on the unique prefix in the session.

    If no session exists, or a CSV file is required which does not exist, a redirect is enforced.

    NOTE: This function does not use the `url_for` function for generating the relative URLs. This
    due the strange behaviour that the relative paths in the templates `url_for` function differs than the
    one generated in the `app`.
    TODO: Ensure that `url_for` is eventually implemented

    Parameters:
        filename: string of filename to use if not using the default
        required: bool whether the CSV file should already exist
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'prefix' not in session:
                return redirect('/')

            if filename:
                csv_file = util.get_temp_file(filename=filename, **session)
            else:
                csv_file = util.get_temp_file(**session)

            if required and not csv_file.exists():
                flash("File not found!", "error")
                return redirect('/')

            return f(csv_file, *args, **kwargs)
        return wrapper
    return decorator
