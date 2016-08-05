import sys
import os.path
import json
import argparse

import OpenGL.GL as gl

import cyglfw3 as glfw

import numpy as np

import pyrr


import gltfutils as gltfu


def setup_glfw(width=900, height=600):
    if not glfw.Init():
        raise Exception('failed to initialize glfw')
    window = glfw.CreateWindow(width, height, "gltfview")
    if not window:
        glfw.Terminate()
        raise Exception('failed to create glfw window')
    # set up glfw callbacks:
    def on_resize(window, width, height):
        gl.glViewport(0, 0, width, height)
    glfw.SetWindowSizeCallback(window, on_resize)
    def on_keydown(window, key, scancode, action, mods):
        # press ESC to quit:
        if (key == glfw.KEY_ESCAPE and action == glfw.PRESS):
            glfw.SetWindowShouldClose(window, gl.GL_TRUE)
    glfw.SetKeyCallback(window, on_keydown)
    glfw.MakeContextCurrent(window)
    print('GL_VERSION: %s' % gl.glGetString(gl.GL_VERSION))
    on_resize(window, width, height)
    return window


def render_scene(scene, gltf, projection_matrix, view_matrix):
    nodes = [gltf['nodes'][n] for n in scene['nodes']]
    for node in nodes:
        gltfu.draw_node(node, gltf,
                        projection_matrix=projection_matrix,
                        view_matrix=view_matrix)


def show_gltf(gltf, uri_path, scene_name=None):
    if scene_name is None:
        scene_name = gltf['scene']
    scene = gltf['scenes'][scene_name]
    window = setup_glfw()

    gltfu.setup_shaders(gltf, uri_path)
    gltfu.setup_programs(gltf)
    gltfu.setup_textures(gltf, uri_path)
    gltfu.setup_buffers(gltf, uri_path)

    nodes = [gltf['nodes'][n] for n in scene['nodes']]
    for node in nodes:
        gltfu.update_world_matrices(node, gltf)
    for node in nodes:
        if 'camera' in node:
            camera = gltf['cameras'][node['camera']]
            if 'perspective' in camera:
                perspective = camera['perspective']
                projection_matrix = pyrr.matrix44.create_perspective_projection_matrix(perspective['yfov'] * (180 / np.pi), perspective['aspectRatio'], perspective['znear'], perspective['zfar']).T
                #projection_matrix = calc_projection_matrix(**perspective)
            elif 'orthographic' in camera:
                raise Exception('TODO')
            view_matrix = np.linalg.inv(node['world_matrix'])
            break
    if projection_matrix is None:
        print('* using default projection matrix (no camera was defined)')
        projection_matrix = pyrr.matrix44.create_perspective_projection_matrix(np.pi / 2.5 * (180 / np.pi), 1.5, 0.1, 1000).T
        #projection_matrix = calc_projection_matrix(aspectRatio=1.5, yfov=np.pi/2.5)
    if view_matrix is None:
        print('* using default view matrix (no camera was defined)')
        view_matrix = np.eye(4)
        view_matrix[2, 3] = -10

    print('* starting render loop...')
    sys.stdout.flush()

    gl.glClearColor(0.1, 0.2, 0.3, 1.0);

    while not glfw.WindowShouldClose(window):
        glfw.PollEvents()
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT);
        
        render_scene(scene, gltf, projection_matrix, view_matrix)

        glfw.SwapBuffers(window)

    glfw.DestroyWindow(window)
    glfw.Terminate()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', help='path of glTF file to view')
    parser.add_argument("--openvr", help="view in VR (using OpenVR viewer)",
                        action="store_true")
    args = parser.parse_args()

    uri_path = os.path.dirname(args.filename)
    gltf = None
    try:
        gltf = json.loads(open(args.filename).read())
        print('* loaded "%s"' % args.filename)
    except Exception as err:
        raise Exception('failed to load %s:\n%s' % (args.filename, err))

    gltf = gltfu.JSobject(gltf)

    if args.openvr:
        from OpenVRRenderer import OpenVRRenderer
        renderer = OpenVRRenderer()
        renderer.set_scene(gltf, uri_path, gltf.scene)
        renderer.start_render_loop()
    else:
        show_gltf(gltf, uri_path)
