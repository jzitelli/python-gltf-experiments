try: # python 3.3 or later
    from types import MappingProxyType
except ImportError as err:
    MappingProxyType = dict

import numpy as np

import pyrr


GLTF_BUFFERVIEW_TYPE_SIZES = MappingProxyType({
    'SCALAR': 1,
    'VEC2': 2,
    'VEC3': 3,
    'VEC4': 4,
    'MAT2': 4,
    'MAT3': 9,
    'MAT4': 16
})


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


class Node(object):
    def __init__(self, gltf_node, gltf_nodes):
        if 'translation' in gltf_node:
            self.translation = np.array(gltf_node.translation, dtype=np.float64)
        if 'quaternion' in gltf_node:
            self.quaternion = np.array(gltf_node.quaternion, dtype=np.float64)
        if 'scale' in gltf_node:
            self.scale = np.array(gltf_node.scale, dtype=np.float64)
        if 'matrix' in gltf_node:
            self.matrix = np.array(gltf_node.matrix, dtype=np.float64).reshape((4,4))
        else:
            self.update_matrix()
        self.children = [Node(gltf_nodes[node_name], gltf_nodes)
                         for node_name in gltf_node.children]
        self.matrix_needs_update = False
    def update_matrix(self):
        if self.matrix_needs_update:
            self.matrix = pyrr.matrix44.create_from_translation(self.translation) @ pyrr.matrix44.create_from_quaternion(self.quaternion) @ pyrr.matrix44.create_from_scale(self.scale)
            self.matrix_needs_update = False
    def update_world_matrices(self, world_matrix=None):
        self.update_matrix()
        if world_matrix is None:
            world_matrix = self.matrix
        else:
            world_matrix = world_matrix @ self.matrix
        self.world_matrix = world_matrix
        for child in self.children:
            child.update_world_matrices(world_matrix=world_matrix)


class Scene(JSobject):
    def __init__(self, gltf_dict, scene=None):
        JSobject.__init__(self, gltf_dict)
        self.nodes = {node_name: Node(gltf_node, self.nodes)
                      for node_name, gltf_node in self.nodes.items()}
        _scene = self.pop('scene')
        if scene is None:
            scene = _scene
        scenes = self.pop('scenes')
        self.root_nodes = [self.nodes[node_name] for node_name in scenes[scene].nodes]
    def update_world_matrices(self):
        for node in self.root_nodes:
            node.update_world_matrices()
