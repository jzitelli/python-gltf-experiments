from copy import deepcopy

try: # python 3.3 or later
    from types import MappingProxyType
except ImportError as err:
    MappingProxyType = dict


GLTF_BUFFERVIEW_TYPE_SIZES = MappingProxyType({
    'SCALAR': 1,
    'VEC2': 2,
    'VEC3': 3,
    'VEC4': 4,
    'MAT2': 4,
    'MAT3': 9,
    'MAT4': 16
})


class JSobject(dict):
    """Object-based representation (rather than dict) of JSON data.
    Useful for interactively exploring JSON data via ipython tab-completion."""
    def __init__(self, json_dict):
        dict.__init__(self)
        d = {}
        for k, v in json_dict.items():
            if k in self.__dict__:
                raise Exception('attribute name collision: %s' % k)
            if isinstance(v, dict):
                d[k] = JSobject(v)
            else:
                d[k] = v
        self.__dict__.update(d)
        self.update(d)
    def __setattr__(self, k, v):
        # TODO: override __setattr__
        dict.__setattr__(self, k, v)


class Scene(JSobject):
    def __init__(self, gltf_dict):
        scene_dict = deepcopy(gltf_dict)
        scenes = scene_dict.pop('scenes')
        scene = scenes[scene_dict.pop('scene')]
        nodes = scene_dict.pop('nodes')
        scene_dict['nodes'] = [nodes[n] for n in scene['nodes']]
        JSobject.__init__(self, scene_dict)
    def update_world_matrices(self):
        for node in self.nodes:
            print(node)
