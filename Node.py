import numpy as np

import pyrr


class Node(object):
    def __init__(self, gltf_node, gltf_nodes):
        if 'matrix' in gltf_node:
            self.matrix = np.array(gltf_node.matrix, dtype=np.float64).reshape((4,4))
            self.translation = self.matrix[:3, 3]
            self.scale = np.array([np.linalg.norm(self.matrix[:3, j]) for j in (0,1,2)])
            if np.linalg.det(self.matrix) < 0:
                self.scale[0] *= -1
            # TODO:
            # self.rotation = pyrr.quaternion.
        else:
            self.translation = np.array(gltf_node.translation, dtype=np.float64)
            self.rotation = np.array(gltf_node.rotation, dtype=np.float64)
            self.scale = np.array(gltf_node.scale, dtype=np.float64)
            self.update_matrix()
        self.children = [Node(gltf_nodes[node_name], gltf_nodes)
                         for node_name in gltf_node.children]
        self.matrix_needs_update = False
    def update_matrix(self):
        if self.matrix_needs_update:
            self.matrix = pyrr.matrix44.create_from_quaternion(self.rotation)
            self.matrix.diagonal()[:3] *= self.scale
            self.matrix[:3, 3] = self.translation
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
