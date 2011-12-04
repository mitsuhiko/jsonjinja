from templatetk.config import Config as ConfigBase, Undefined
from weakref import ref as weakref


def grab_wire_object_details(obj):
    if isinstance(obj, dict) and '__jsonjinja_wire__' in obj:
        return obj['__jsonjinja_wire__']


class Config(ConfigBase):

    def __init__(self, environment):
        ConfigBase.__init__(self)
        self._environment = weakref(environment)
        self.forloop_parent_access = True

    @property
    def environment(self):
        return self._environment()

    def get_autoescape_default(self, name):
        return name.endswith(('.html', '.xml'))

    def mark_safe(self, value):
        return self.markup_type(self.to_unicode(value))

    def get_template(self, name):
        return self.environment.get_template(name)

    def yield_from_template(self, template, info, vars=None):
        return template.execute(vars or {}, info)

    def to_unicode(self, value):
        if value is None or self.is_undefined(value):
            return u''
        if isinstance(value, bool):
            return value and u'true' or u'false'
        if isinstance(value, float):
            if int(value) == value:
                return unicode(int(value))
            return unicode(value)
        if isinstance(value, (int, long, basestring)):
            return unicode(value)
        wod = grab_wire_object_details(value)
        if wod == 'html-safe':
            return unicode(value['value'])
        if isinstance(value, (list, dict)):
            raise TypeError('Cannot print objects, tried to '
                            'print %r' % value)
        return unicode(value)

    def getattr(self, obj, attribute):
        try:
            return obj[attribute]
        except (TypeError, LookupError):
            try:
                obj[int(attribute)]
            except ValueError:
                try:
                    return getattr(obj, str(attribute))
                except (UnicodeError, AttributeError):
                    pass
        return Undefined()

    getitem = getattr
