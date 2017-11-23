"""For the dict-subclass JSobject (defined below),
user-defined attribute names may collide with
the inherited dict methods (e.g. "keys", "values", "items", etc),
overwriting the inherited binding.  For these special cases,
the built-in dict methods are also bound to corresponding '__'-prefixed
attribute names (e.g. "__keys", "__values", "__items", etc)."""
_JSOBJECT_DICT_ATTR_RENAMES = {k: '__%s' % k
                               for k in {}.__dir__()
                               if not k.startswith('__')}


class JSobject(dict):
    """Python object-based representation of JSON data.
    Useful for interactively exploring JSON data via ipython tab-completion."""
    _BAD_NAMES = frozenset([name for name in {}.__dir__()
                            if name not in _JSOBJECT_DICT_ATTR_RENAMES])
    def __init__(self, json_dict):
        dict.__init__(self)
        for name, rename in _JSOBJECT_DICT_ATTR_RENAMES.items():
            dict.__setattr__(self, rename, self.__getattribute__(name))
        for k, v in json_dict.items():
            self[k] = v
    def __setattr__(self, k, v):
        if k in JSobject._BAD_NAMES:
            raise Exception('attribute name collision: %s' % k)
        if isinstance(v, dict):
            v = JSobject(v)
        dict.__setitem__(self, k, v)
        dict.__setattr__(self, k, v)
    def __setitem__(self, k, v):
        self.__setattr__(k, v)
    def __delattr__(self, k):
        dict.__delitem__(self, k)
        dict.__delattr__(self, k)
    def __delitem__(self, k):
        self.__delattr__(k)
