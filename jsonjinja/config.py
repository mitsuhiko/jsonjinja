from templatetk.config import Config as ConfigBase, Undefined
from weakref import ref as weakref


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
