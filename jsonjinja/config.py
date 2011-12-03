from templatetk.config import Config as ConfigBase, Undefined
from templatetk.runtime import LoopContext as LoopContextBase
from weakref import ref as weakref


class LoopContext(LoopContextBase):

    def __init__(self, iterator, parent):
        LoopContextBase.__init__(self, iterator)
        self.parent = parent


class Config(ConfigBase):

    def __init__(self, environment):
        ConfigBase.__init__(self)
        self._environment = weakref(environment)
        self.forloop_parent_access = True

    def wrap_loop(self, iterator, parent=None):
        return LoopContext(iterator, parent)

    @property
    def environment(self):
        return self._environment()

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
