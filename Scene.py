from JSobject import JSobject
from Node import Node


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
