#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2017-2018 nic.at GmbH <wagner@cert.at>
# SPDX-License-Identifier: AGPL-3.0
import os

from setuptools import find_packages, setup

DATA = [
    ('/opt/intelmq/etc/examples',
     ['intelmq_webinput_csv/etc/webinput_csv.conf',
      ],
     ),
]

exec(open(os.path.join(os.path.dirname(__file__),
                       'intelmq_webinput_csv/version.py')).read())  # defines __version__
with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as handle:
    README = handle.read().replace('<docs/',
                                   '<https://github.com/certat/intelmq-webinput-csv/blob/master/docs/')

setup(
    name='intelmq_webinput_csv',
    version=__version__,
    maintainer='Sebastian Wagner',
    maintainer_email='wagner@cert.at',
    install_requires=[
        'Flask',
        'intelmq',
        ],
    test_suite='intelmq_webinput_csv.tests',
    packages=find_packages(),
    package_data={'intelmq_webinput_csv': [
        'etc/webinput.conf',
        'static/',
    ]
    },
    include_package_data=True,
    url='https://github.com/certat/intelmq_webinput_csv/',
    license='AGPLv3 and MIT and OFL-1.1',
    description='This is a Flask-based web interface allowing the user to '
                'insert data into intelmq\'s pipelines interactively with '
                'preview from the parser.',
    long_description=README,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Flask',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Telecommunications Industry',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Security',
    ],
    keywords='incident handling cert csirt',
    data_files=DATA,
    entry_points={
        'console_scripts': [
            'intelmq_webinput_csv=intelmq_webinput_csv.bin.backend:main',
        ],
    },
)
