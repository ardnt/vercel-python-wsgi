from jinja2 import Environment, select_autoescape, FileSystemLoader
from pprint import pformat
import copy
import re
import sys
import os
import json
import base64
from io import BytesIO
from datetime import datetime
from werkzeug.datastructures import Headers
from collections.abc import Mapping
from werkzeug._internal import _wsgi_encoding_dance, _to_bytes
if sys.version_info[0] < 3:
    from urllib import unquote, urlencode
    from urlparse import urlparse
else:
    from urllib.parse import urlparse, unquote, urlencode

from .handler import get_env

PATH = os.path.dirname(os.path.abspath(__file__))

templateEnv = Environment(loader=FileSystemLoader(PATH + '/templates/'),
                          autoescape=select_autoescape())
dt_string = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

'The code was taken from Django repository'


class MultiValueDict(dict):
    """
    A subclass of dictionary customized to handle multiple values for the
    same key.
    >>> d = MultiValueDict({'name': ['Adrian', 'Simon'], 'position': ['Developer']})
    >>> d['name']
    'Simon'
    >>> d.getlist('name')
    ['Adrian', 'Simon']
    >>> d.getlist('doesnotexist')
    []
    >>> d.getlist('doesnotexist', ['Adrian', 'Simon'])
    ['Adrian', 'Simon']
    >>> d.get('lastname', 'nonexistent')
    'nonexistent'
    >>> d.setlist('lastname', ['Holovaty', 'Willison'])
    This class exists to solve the irritating problem raised by cgi.parse_qs,
    which returns a list for every key, even though most web forms submit
    single name-value pairs.
    """
    def __init__(self, key_to_list_mapping=()):
        super().__init__(key_to_list_mapping)

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, super().__repr__())

    def __getitem__(self, key):
        """
        Return the last data value for this key, or [] if it's an empty list;
        raise KeyError if not found.
        """
        try:
            list_ = super().__getitem__(key)
        except KeyError:
            raise KeyError(key)
        try:
            return list_[-1]
        except IndexError:
            return []

    def __setitem__(self, key, value):
        super().__setitem__(key, [value])

    def __copy__(self):
        return self.__class__([(k, v[:]) for k, v in self.lists()])

    def __deepcopy__(self, memo):
        result = self.__class__()
        memo[id(self)] = result
        for key, value in dict.items(self):
            dict.__setitem__(result, copy.deepcopy(key, memo),
                             copy.deepcopy(value, memo))
        return result

    def __getstate__(self):
        return {**self.__dict__, '_data': {k: self._getlist(k) for k in self}}

    def __setstate__(self, obj_dict):
        data = obj_dict.pop('_data', {})
        for k, v in data.items():
            self.setlist(k, v)
        self.__dict__.update(obj_dict)

    def get(self, key, default=None):
        """
        Return the last data value for the passed key. If key doesn't exist
        or value is an empty list, return `default`.
        """
        try:
            val = self[key]
        except KeyError:
            return default
        if val == []:
            return default
        return val

    def _getlist(self, key, default=None, force_list=False):
        """
        Return a list of values for the key.
        Used internally to manipulate values list. If force_list is True,
        return a new copy of values.
        """
        try:
            values = super().__getitem__(key)
        except KeyError:
            if default is None:
                return []
            return default
        else:
            if force_list:
                values = list(values) if values is not None else None
            return values

    def getlist(self, key, default=None):
        """
        Return the list of values for the key. If key doesn't exist, return a
        default value.
        """
        return self._getlist(key, default, force_list=True)

    def setlist(self, key, list_):
        super().__setitem__(key, list_)

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
            # Do not return default here because __setitem__() may store
            # another value -- QueryDict.__setitem__() does. Look it up.
        return self[key]

    def setlistdefault(self, key, default_list=None):
        if key not in self:
            if default_list is None:
                default_list = []
            self.setlist(key, default_list)
            # Do not return default_list here because setlist() may store
            # another value -- QueryDict.setlist() does. Look it up.
        return self._getlist(key)

    def appendlist(self, key, value):
        """Append an item to the internal list associated with key."""
        self.setlistdefault(key).append(value)

    def items(self):
        """
        Yield (key, value) pairs, where value is the last item in the list
        associated with the key.
        """
        for key in self:
            yield key, self[key]

    def lists(self):
        """Yield (key, list) pairs."""
        return iter(super().items())

    def values(self):
        """Yield the last value on every key list."""
        for key in self:
            yield self[key]

    def copy(self):
        """Return a shallow copy of this object."""
        return copy.copy(self)

    def update(self, *args, **kwargs):
        """Extend rather than replace existing key lists."""
        if len(args) > 1:
            raise TypeError("update expected at most 1 argument, got %d" %
                            len(args))
        if args:
            arg = args[0]
            if isinstance(arg, MultiValueDict):
                for key, value_list in arg.lists():
                    self.setlistdefault(key).extend(value_list)
            else:
                if isinstance(arg, Mapping):
                    arg = arg.items()
                for key, value in arg:
                    self.setlistdefault(key).append(value)
        for key, value in kwargs.items():
            self.setlistdefault(key).append(value)

    def dict(self):
        """Return current object as a dict with singular values."""
        return {key: self[key] for key in self}


class SafeExceptionReporterFilter:
    """
    Use annotations made by the sensitive_post_parameters and
    sensitive_variables decorators to filter out sensitive information.
    """
    cleansed_substitute = '********************'
    hidden_settings = re.compile('API|TOKEN|KEY|SECRET|PASS|SIGNATURE',
                                 flags=(re.I, re.IGNORECASE))

    def cleanse_setting(self, key, value):
        """
        Cleanse an individual setting key/value of sensitive content. If the
        value is a dictionary, recursively cleanse the keys in that dictionary.
        """
        try:
            is_sensitive = self.hidden_settings.search(key)
        except TypeError:
            is_sensitive = False

        if is_sensitive:
            cleansed = self.cleansed_substitute
        elif isinstance(value, dict):
            cleansed = {
                k: self.cleanse_setting(k, v)
                for k, v in value.items()
            }
        elif isinstance(value, list):
            cleansed = [self.cleanse_setting('', v) for v in value]
        elif isinstance(value, tuple):
            cleansed = tuple(self.cleanse_setting('', v) for v in value)
        else:
            cleansed = value

        if callable(cleansed):
            cleansed = CallableSettingWrapper(cleansed)

        return cleansed

    def get_safe_request_meta(self, request):
        """
        Return a dictionary of request.META with sensitive values redacted.
        """
        if request is None:
            return {}

        return {k: self.cleanse_setting(k, v) for k, v in request.items()}

    def get_cleansed_multivaluedict(self, request, multivaluedict):
        """
        Replace the keys in a MultiValueDict marked as sensitive with stars.
        This mitigates leaking sensitive POST parameters if something like
        request.POST['nonexistent_key'] throws an exception (#21098).
        """
        sensitive_post_parameters = getattr(request,
                                            'sensitive_post_parameters', [])
        if sensitive_post_parameters:
            multivaluedict = multivaluedict.copy()
            for param in sensitive_post_parameters:
                if param in multivaluedict:
                    multivaluedict[param] = self.cleansed_substitute
        return multivaluedict

    def get_post_parameters(self, request):
        """
        Replace the values of POST parameters marked as sensitive with
        stars (*********).
        """
        if request is None:
            return {}
        sensitive_post_parameters = getattr(request,
                                            'sensitive_post_parameters', [])
        if not sensitive_post_parameters:
            # return request.POST
            return {}

        cleansed = request.POST.copy()
        if sensitive_post_parameters == '__ALL__':
            # Cleanse all parameters.
            for k in cleansed:
                cleansed[k] = self.cleansed_substitute
        else:
            # Cleanse only the specified parameters.
            for param in sensitive_post_parameters:
                if param in cleansed:
                    cleansed[param] = self.cleansed_substitute
        return cleansed

    def cleanse_special_types(self, request, value):
        try:
            # If value is lazy or a complex object of another kind, this check
            # might raise an exception. isinstance checks that lazy
            # MultiValueDicts will have a return value.
            is_multivalue_dict = isinstance(value, MultiValueDict)
        except Exception as e:
            return '{!r} while evaluating {!r}'.format(e, value)

        if is_multivalue_dict:
            # Cleanse MultiValueDicts (request.POST is the one we usually care about)
            value = self.get_cleansed_multivaluedict(request, value)
        return value

    def get_traceback_frame_variables(self, request, tb_frame):
        """
        Replace the values of variables marked as sensitive with
        stars (*********).
        """
        # Loop through the frame's callers to see if the sensitive_variables
        # decorator was used.
        current_frame = tb_frame.f_back
        sensitive_variables = None
        while current_frame is not None:
            if (current_frame.f_code.co_name == 'sensitive_variables_wrapper'
                    and 'sensitive_variables_wrapper'
                    in current_frame.f_locals):
                # The sensitive_variables decorator was used, so we take note
                # of the sensitive variables' names.
                wrapper = current_frame.f_locals['sensitive_variables_wrapper']
                sensitive_variables = getattr(wrapper, 'sensitive_variables',
                                              None)
                break
            current_frame = current_frame.f_back

        cleansed = {}
        if sensitive_variables:
            if sensitive_variables == '__ALL__':
                # Cleanse all variables
                for name in tb_frame.f_locals:
                    cleansed[name] = self.cleansed_substitute
            else:
                # Cleanse specified variables
                for name, value in tb_frame.f_locals.items():
                    if name in sensitive_variables:
                        value = self.cleansed_substitute
                    else:
                        value = self.cleanse_special_types(request, value)
                    cleansed[name] = value
        else:
            # Potentially cleanse the request and any MultiValueDicts if they
            # are one of the frame variables.
            for name, value in tb_frame.f_locals.items():
                cleansed[name] = self.cleanse_special_types(request, value)

        if (tb_frame.f_code.co_name == 'sensitive_variables_wrapper'
                and 'sensitive_variables_wrapper' in tb_frame.f_locals):
            # For good measure, obfuscate the decorated function's arguments in
            # the sensitive_variables decorator's frame, in case the variables
            # associated with those arguments were meant to be obfuscated from
            # the decorated function's frame.
            cleansed['func_args'] = self.cleansed_substitute
            cleansed['func_kwargs'] = self.cleansed_substitute

        return cleansed.items()


class ExceptionReporter:
    """Organize and coordinate reporting on exceptions."""
    def __init__(self, lambda_event=None, context=None):
        self.filter = SafeExceptionReporterFilter()
        self.context = context
        self.exc_type, self.exc_value, self.tb = sys.exc_info()
        self.request = None
        if lambda_event is not None:
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
                'CONTENT_TYPE': headers.get('content-type', ''),
                'PATH_INFO': parsed_url.path,
                'QUERY_STRING': unquote(parsed_url.query),
                'REMOTE_ADDR': event.get('x-real-ip', ''),
                'REQUEST_METHOD': event.get('method', 'GET'),
                'SCRIPT_NAME': '',
                'SERVER_NAME': headers.get('host', 'lambda'),
                'SERVER_PORT': headers.get('x-forwarded-port', '443'),
                'SERVER_PROTOCOL': 'HTTP/2',
                'wsgi.input': BytesIO(body),
                'wsgi.multiprocess': False,
                'wsgi.multithread': False,
                'wsgi.run_once': False,
                'wsgi.url_scheme': headers.get('scheme', 'https'),
                'wsgi.version': (1, 0),
            }

            for key, value in environ.items():
                if isinstance(value, str):
                    environ[key] = _wsgi_encoding_dance(value)

            for key, value in headers.items():
                key = 'HTTP_' + key.upper().replace('-', '_')
                if key not in ('HTTP_CONTENT_TYPE', 'HTTP_CONTENT_LENGTH'):
                    environ[key] = value
            self.request = environ
        

    def _pprint(self, value):
        """A wrapper around pprint.pprint -- for debugging, really."""
        try:
            return pformat(value)
        except Exception as e:
            return "Error in formatting: %s: %s" % (e.__class__.__name__, e)

    def _force_str(self, s, encoding='utf-8', errors='strict'):
        """
        Similar to smart_str(), except that lazy instances are resolved to
        strings, rather than kept as lazy objects.
        If strings_only is True, don't convert (some) non-string-like objects.
        """
        # Handle the common case first for performance reasons.
        if not issubclass(type(s), str):
            s = str(s, encoding, errors) if isinstance(s, bytes) else str(s)
        return s

    def _get_raw_insecure_uri(self):
        """
        Return an absolute URI from variables available in this request. Skip
        allowed hosts protection, so may return insecure URI.
        """
        return ('{scheme}://{host}{path}').format(
            scheme=self.request['wsgi.url_scheme'],
            host=self.request['SERVER_NAME'],
            path=self.request['PATH_INFO'],
            # scheme='https',
            # host='localhost',
            # path='/',
        )

    def get_traceback_data(self):
        """Return a dictionary containing traceback information."""

        frames = self.get_traceback_frames()
        for i, frame in enumerate(frames):
            if 'vars' in frame:
                frame_vars = []
                for k, v in frame['vars']:
                    v = self._pprint(v)
                    # Trim large blobs of data
                    if len(v) > 4096:
                        v = '%s… <trimmed %d bytes string>' % (v[0:4096],
                                                               len(v))
                    frame_vars.append((k, v))
                frame['vars'] = frame_vars
            frames[i] = frame

        unicode_hint = ''
        if self.exc_type and issubclass(self.exc_type, UnicodeError):
            start = getattr(self.exc_value, 'start', None)
            end = getattr(self.exc_value, 'end', None)
            if start is not None and end is not None:
                unicode_str = self.exc_value.args[1]
                unicode_hint = self.force_str(
                    unicode_str[max(start - 5, 0):min(end +
                                                      5, len(unicode_str))],
                    'ascii',
                    errors='replace')

        c = {
            'unicode_hint':
            unicode_hint,
            'frames':
            frames,
            'request':
            self.request,
            'request_meta':
            self.filter.get_safe_request_meta(self.request),
            'filtered_POST_items':
            list(self.filter.get_post_parameters(self.request).items()),
            'sys_executable':
            sys.executable,
            'sys_version_info':
            '%d.%d.%d' % sys.version_info[0:3],
            'server_time':
            dt_string,
            'sys_path':
            sys.path,
        }
        if self.request is not None:
            # c['request_GET_items'] = self.request.GET.items()
            # c['request_FILES_items'] = self.request.FILES.items()
            # c['request_COOKIES_items'] = self.request.COOKIES.items()
            c['request_GET_items'] = {}.items()
            c['request_FILES_items'] = {}.items()
            c['request_COOKIES_items'] = {}.items()
            c['request_insecure_uri'] = self._get_raw_insecure_uri()

        # Check whether exception info is available
        if self.exc_type:
            c['exception_type'] = self.exc_type.__name__
        if self.exc_value:
            c['exception_value'] = str(self.exc_value)
        if frames:
            c['lastframe'] = frames[-1]
        return c

    def get_traceback_html(self):
        """Return HTML version of debug 500 HTTP error page."""

        t = templateEnv.get_template('500.html')
        c = self.get_traceback_data()
        return t.render(**c)

    def _get_source(self, filename, loader, module_name):
        source = None
        if hasattr(loader, 'get_source'):
            try:
                source = loader.get_source(module_name)
            except ImportError:
                pass
            if source is not None:
                source = source.splitlines()
        if source is None:
            try:
                with open(filename, 'rb') as fp:
                    source = fp.read().splitlines()
            except OSError:
                pass
        return source

    def _get_lines_from_file(self,
                             filename,
                             lineno,
                             context_lines,
                             loader=None,
                             module_name=None):
        """
        Return context_lines before and after lineno from file.
        Return (pre_context_lineno, pre_context, context_line, post_context).
        """
        source = self._get_source(filename, loader, module_name)
        if source is None:
            return None, [], None, []

        # If we just read the source from a file, or if the loader did not
        # apply tokenize.detect_encoding to decode the source into a
        # string, then we should do that ourselves.
        if isinstance(source[0], bytes):
            encoding = 'ascii'
            for line in source[:2]:
                # File coding may be specified. Match pattern from PEP-263
                # (https://www.python.org/dev/peps/pep-0263/)
                match = re.search(br'coding[:=]\s*([-\w.]+)', line)
                if match:
                    encoding = match[1].decode('ascii')
                    break
            source = [str(sline, encoding, 'replace') for sline in source]

        lower_bound = max(0, lineno - context_lines)
        upper_bound = lineno + context_lines

        try:
            pre_context = source[lower_bound:lineno]
            context_line = source[lineno]
            post_context = source[lineno + 1:upper_bound]
        except IndexError:
            return None, [], None, []
        return lower_bound, pre_context, context_line, post_context

    def _get_explicit_or_implicit_cause(self, exc_value):
        explicit = getattr(exc_value, '__cause__', None)
        suppress_context = getattr(exc_value, '__suppress_context__', None)
        implicit = getattr(exc_value, '__context__', None)
        return explicit or (None if suppress_context else implicit)

    def get_traceback_frames(self):
        # Get the exception and all its causes
        exceptions = []
        exc_value = self.exc_value
        while exc_value:
            exceptions.append(exc_value)
            exc_value = self._get_explicit_or_implicit_cause(exc_value)
            if exc_value in exceptions:
                # Avoid infinite loop if there's a cyclic reference (#29393).
                break

        frames = []
        # No exceptions were supplied to ExceptionReporter
        if not exceptions:
            return frames

        # In case there's just one exception, take the traceback from self.tb
        exc_value = exceptions.pop()
        tb = self.tb if not exceptions else exc_value.__traceback__
        while True:
            frames.extend(self.get_exception_traceback_frames(exc_value, tb))
            try:
                exc_value = exceptions.pop()
            except IndexError:
                break
            tb = exc_value.__traceback__
        return frames

    def get_exception_traceback_frames(self, exc_value, tb):
        exc_cause = self._get_explicit_or_implicit_cause(exc_value)
        exc_cause_explicit = getattr(exc_value, '__cause__', True)
        if tb is None:
            yield {
                'exc_cause': exc_cause,
                'exc_cause_explicit': exc_cause_explicit,
                'tb': None,
                'type': 'user',
            }
        while tb is not None:
            # Support for __traceback_hide__ which is used by a few libraries
            # to hide internal frames.
            if tb.tb_frame.f_locals.get('__traceback_hide__'):
                tb = tb.tb_next
                continue
            filename = tb.tb_frame.f_code.co_filename
            function = tb.tb_frame.f_code.co_name
            lineno = tb.tb_lineno - 1
            loader = tb.tb_frame.f_globals.get('__loader__')
            module_name = tb.tb_frame.f_globals.get('__name__') or ''
            pre_context_lineno, pre_context, context_line, post_context = self._get_lines_from_file(
                filename,
                lineno,
                7,
                loader,
                module_name,
            )
            if pre_context_lineno is None:
                pre_context_lineno = lineno
                pre_context = []
                context_line = '<source code not available>'
                post_context = []
            yield {
                'exc_cause':
                exc_cause,
                'exc_cause_explicit':
                exc_cause_explicit,
                'tb':
                tb,
                'type':
                'django' if module_name.startswith('django.') else 'user',
                'filename':
                filename,
                'function':
                function,
                'lineno':
                lineno + 1,
                'vars':
                self.filter.get_traceback_frame_variables(
                    self.request, tb.tb_frame),
                'id':
                id(tb),
                'pre_context':
                pre_context,
                'context_line':
                context_line,
                'post_context':
                post_context,
                'pre_context_lineno':
                pre_context_lineno + 1,
            }
            tb = tb.tb_next


class CallableSettingWrapper:
    """
    Object to wrap callable appearing in settings.
    * Not to call in the debug page (#21345).
    * Not to break the debug page if the callable forbidding to set attributes
      (#23070).
    """
    def __init__(self, callable_setting):
        self._wrapped = callable_setting

    def __repr__(self):
        return repr(self._wrapped)