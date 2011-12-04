import os
import errno
from jsonjinja.exceptions import NotJSONCompatibleException


def get_runtime_javascript():
    import templatetk
    import jsonjinja
    runtime_js = [
        os.path.join(os.path.dirname(templatetk.__file__),
                     'res', 'templatetk.runtime.js'),
        os.path.join(os.path.dirname(jsonjinja.__file__),
                     'res', 'jsonjinja.runtime.js')
    ]

    rv = []
    for filename in runtime_js:
        with open(filename) as f:
            rv.append(f.read())
    return ''.join(rv)


def ensure_json_compatible(obj):
    if obj is None:
        return True
    elif isinstance(obj, (basestring, int, long, float)):
        return True
    elif isinstance(obj, list):
        for x in obj:
            ensure_json_compatible(x)
    elif isinstance(obj, dict):
        for k, v in obj.iteritems():
            if not isinstance(k, basestring):
                raise NotJSONCompatibleException(
                    'Dictionary keys must be strings, got %r' % k)
            ensure_json_compatible(v)
    else:
        raise NotJSONCompatibleException('Got unsupported object %r' % obj)


def open_if_exists(filename, mode='rb'):
    """Returns a file descriptor for the filename if that file exists,
    otherwise `None`.
    """
    try:
        return open(filename, mode)
    except IOError, e:
        if e.errno not in (errno.ENOENT, errno.EISDIR):
            raise
