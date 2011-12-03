from templatetk.config import Config as ConfigBase
from weakref import ref as weakref


class Config(ConfigBase):

    def __init__(self, environment):
        ConfigBase.__init__(self)
        self._environment = weakref(environment)

    @property
    def environment(self):
        return self._environment()
