#! /usr/bin/env python
import json

from setuptools import setup


with open('package.json') as f:
    package_data = json.loads(f.read())
    version = package_data['version']

# py-vercel
"""A barebones setup for tests
"""
setup(
    name='py-vercel',
    version=version,
    packages=[
        'pyvercel'
    ],
    install_requires=[
        'Werkzeug>=2.0.1',
        'py-exceptions'
    ]
)
