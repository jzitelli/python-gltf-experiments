import numpy as np

import OpenGL.GL as gl

import pyrr


import gltfutils as gltfu


class OpenGLRenderer(object):
    def __init__(self):
        self.projection_matrix = pyrr.matrix44.create_perspective_projection_matrix(np.rad2deg(np.pi / 2.5), 1.5, 0.1, 1000).T
        self.view_matrix = np.eye(4)
        self.view_matrix[2, 3] = -10
    def set_scene(self, gltf, uri_path, scene_name=None):
        if scene_name is None:
            scene_name = gltf.scene
        gltfu.setup_shaders(gltf, uri_path)
        gltfu.setup_programs(gltf)
        gltfu.setup_textures(gltf, uri_path)
        gltfu.setup_buffers(gltf, uri_path)
        self.gltf = gltf
        scene = gltf.scenes[scene_name]
        self.nodes = [self.gltf.nodes[n] for n in scene.nodes]
        for node in self.nodes:
            gltfu.update_world_matrices(node, gltf)
        for node in self.nodes:
            if 'camera' in node:
                camera = gltf['cameras'][node['camera']]
                if 'perspective' in camera:
                    perspective = camera['perspective']
                    self.projection_matrix = pyrr.matrix44.create_perspective_projection_matrix(np.rad2deg(perspective['yfov']), perspective['aspectRatio'],
                                                                                                perspective['znear'], perspective['zfar'])
                elif 'orthographic' in camera:
                    raise Exception('TODO')
                self.view_matrix = np.linalg.inv(node['world_matrix'])
                break
    def render(self):
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        for node in self.nodes:
            gltfu.draw_node(node, self.gltf,
                            projection_matrix=self.projection_matrix,
                            view_matrix=self.view_matrix)
