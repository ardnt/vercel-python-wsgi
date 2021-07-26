#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Python WSGI AWS Lambda handler

Inspired by Zappa and Serverless AWS handlers
License: MIT
"""

import base64
import json
import logging
from importlib import import_module
import os
import sys
from traceback import format_exc
from .app import application as traceback_app

from werkzeug.datastructures import Headers
from werkzeug.wrappers import Response
from io import BytesIO
from werkzeug._internal import _wsgi_encoding_dance, _to_bytes
if sys.version_info[0] < 3:
    from urllib import unquote, urlencode
    from urlparse import urlparse
else:
    from urllib.parse import urlparse, unquote, urlencode

# Set up logging
root = logging.getLogger()
if root.handlers:
    for handler in root.handlers:
        root.removeHandler(handler)
logging.basicConfig()

# List of MIME types that should not be base64 encoded. MIME types within
# `text/*` are included by default.
TEXT_MIME_TYPES = [
    'application/json',
    'application/javascript',
    'application/xml',
    'application/vnd.api+json',
    'image/svg+xml',
]


def handler(app, lambda_event, context, error=None):

    event = json.loads(lambda_event['body'])
    headers = Headers(event.get('headers', None))
    parsed_url = urlparse(event['path'])

    body = event.get('body', '')
    encoding = event.get('encoding', None)

    if encoding == 'base64':
        body = base64.b64decode(body)
    else:
        body = _to_bytes(body, charset='utf-8')

    environ = {
        'CONTENT_LENGTH': str(len(body)),
        'CONTENT_TYPE': headers.get('Content-Type', ''),
        'PATH_INFO': parsed_url.path,
        'QUERY_STRING': unquote(parsed_url.query),
        'REMOTE_ADDR': event.get('x-real-ip', ''),
        'REQUEST_METHOD': event['method'],
        'SCRIPT_NAME': '',
        'SERVER_NAME': headers.get('Host', 'lambda'),
        'SERVER_PORT': headers.get('X-Forwarded-Port', '80'),
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'event': lambda_event['body'],
        'wsgi.errors': sys.stderr,
        'wsgi.input': BytesIO(body),
        'wsgi.multiprocess': False,
        'wsgi.multithread': False,
        'wsgi.run_once': False,
        'wsgi.url_scheme': headers.get('X-Forwarded-Proto', 'http'),
        'wsgi.version': (1, 0),
    }
    if error:
        environ['PATH_INFO'] = '/'
        environ['QUERY_STRING'] = unquote(urlencode(error))

    for key, value in environ.items():
        if isinstance(value, str):
            environ[key] = _wsgi_encoding_dance(value)

    for key, value in headers.items():
        key = 'HTTP_' + key.upper().replace('-', '_')
        if key not in ('HTTP_CONTENT_TYPE', 'HTTP_CONTENT_LENGTH'):
            environ[key] = value

    response = Response.from_app(app, environ)

    # Handle multi-value headers
    headers = {}
    for key, value in response.headers:
        if key in headers:
            current_value = headers[key]
            if isinstance(current_value, list):
                headers[key] += [value]
            else:
                headers[key] = [current_value, value]
        else:
            headers[key] = value

    returndict = {
        'statusCode': response.status_code,
        'headers': headers,
        'body': '',
    }

    if response.data:
        mimetype = response.mimetype or 'text/plain'
        if (
            mimetype.startswith('text/') or mimetype in TEXT_MIME_TYPES
        ) and not response.headers.get('Content-Encoding', ''):
            returndict['body'] = response.get_data(as_text=True)
        else:
            returndict['body'] = base64.b64encode(response.data)\
                                       .decode('utf-8')
            returndict['encoding'] = 'base64'

    return returndict


def vercel_handler(event, context):
    wsgi_app_data = os.environ.get('WSGI_APPLICATION').split('.')
    wsgi_module_name = '.'.join(wsgi_app_data[:-1])
    wsgi_app_name = wsgi_app_data[-1]
    try:
        wsgi_module = import_module(wsgi_module_name)
    except Exception:
        return handler(traceback_app, event, context,
                       {'traceback': format_exc(), 'error': 'An error has occurred during app importing'})
        application = getattr(wsgi_module, wsgi_app_name)
    except Exception:
        return handler(traceback_app, event, context,
                       {'traceback': 'Change app name in vercel.json', 'error': 'Wrong application name'})

    return handler(application, event, context)
