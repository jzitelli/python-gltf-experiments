"""
See http://stackoverflow.com/questions/9997176/immutable-dictionary-only-use-as-a-key-for-another-dictionary
"""

from copy import deepcopy

try: # python 3.3 or later
    from types import MappingProxyType
except ImportError as err:
    MappingProxyType = dict

    
# class ImmutableDict(MappingProxyType):
#     def __init__(self, src_dict):
#         MappingProxyType.__init__(self, deepcopy(src_dict))
#         self._hash = hash(frozenset(self.items()))
#     def __hash__(self):
#         return self._hash
#     def __eq__(self, other):
#         return self._hash == other._hash


class ImmutableDict(dict):
    def __init__(self, src_dict):
        dict.__init__(self, deepcopy(src_dict))
        self._hash = hash(frozenset(self.items()))
    def __hash__(self):
        return self._hash
    def __eq__(self, other):
        return self._hash == other._hash
    def __setitem__(self, k, v):
        pass
    def __setattr__(self, k, v):
        pass
    def __delitem__(self, k):
        pass
    def __delattr__(self, k):
        pass
