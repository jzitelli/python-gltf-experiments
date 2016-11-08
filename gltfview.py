import sys
import os.path
import json
import argparse

import numpy as np

import OpenGL
OpenGL.ERROR_CHECKING = False
OpenGL.ERROR_LOGGING = False
OpenGL.ERROR_ON_COPY = True
import OpenGL.GL as gl

import cyglfw3 as glfw

import pyrr

import gltfutils as gltfu
from JSobject import JSobject

try:
    from OpenVRRenderer import OpenVRRenderer
except ImportError:
    OpenVRRenderer = None


def setup_glfw(width=800, height=600, double_buffered=False):
    if not glfw.Init():
        raise Exception('failed to initialize glfw')
    if not double_buffered:
        glfw.WindowHint(glfw.DOUBLEBUFFER, False)
        glfw.SwapInterval(0)
    window = glfw.CreateWindow(width, height, "gltfview")
    if not window:
        glfw.Terminate()
        raise Exception('failed to create glfw window')
    glfw.MakeContextCurrent(window)
    print('GL_VERSION: %s' % gl.glGetString(gl.GL_VERSION))
    return window


def show_gltf(gltf, uri_path, scene_name=None, openvr=False):
    if scene_name is None:
        scene_name = gltf['scene']

    window_size = [800, 600]

    window = setup_glfw(width=window_size[0], height=window_size[1],
                        double_buffered=not openvr)

    if openvr:
        vr_renderer = OpenVRRenderer()

    def on_resize(window, width, height):
        window_size[0], window_size[1] = width, height
    glfw.SetWindowSizeCallback(window, on_resize)

    gl.glClearColor(0.01, 0.01, 0.17, 1.0);

    gltfu.setup_shaders(gltf, uri_path)
    gltfu.setup_programs(gltf)
    gltfu.setup_textures(gltf, uri_path)
    gltfu.setup_buffers(gltf, uri_path)

    scene = gltf.scenes[scene_name]
    nodes = [gltf.nodes[n] for n in scene.nodes]

    world_matrix = np.eye(4, 4)

    for node in nodes:
        gltfu.update_world_matrices(node, gltf)

    for node in nodes:
        if 'camera' in node:
            camera = gltf['cameras'][node['camera']]
            if 'perspective' in camera:
                perspective = camera['perspective']
                projection_matrix = pyrr.matrix44.create_perspective_projection_matrix(np.rad2deg(perspective['yfov']), perspective['aspectRatio'],
                                                                                       perspective['znear'], perspective['zfar'])
            elif 'orthographic' in camera:
                raise Exception('TODO')
            world_matrix = node['world_matrix']
            break

    key_state = {glfw.KEY_W: False,
                 glfw.KEY_S: False,
                 glfw.KEY_A: False,
                 glfw.KEY_D: False}
    def on_keydown(window, key, scancode, action, mods):
        # press ESC to quit:
        if key == glfw.KEY_ESCAPE and action == glfw.PRESS:
            glfw.SetWindowShouldClose(window, gl.GL_TRUE)
        elif action == glfw.PRESS:
            key_state[key] = True
        elif action == glfw.RELEASE:
            key_state[key] = False
    glfw.SetKeyCallback(window, on_keydown)

    move_speed = 0.002

    def process_input():
        glfw.PollEvents()
        if key_state[glfw.KEY_W]:
            world_matrix[2,3] += move_speed
        if key_state[glfw.KEY_S]:
            world_matrix[2,3] -= move_speed
        if key_state[glfw.KEY_A]:
            world_matrix[0,3] += move_speed
        if key_state[glfw.KEY_D]:
            world_matrix[0,3] -= move_speed

    print('* starting render loop...')
    sys.stdout.flush()

    stats_printed = False
    while not glfw.WindowShouldClose(window):
        process_input()
        if openvr:
            vr_renderer.render(gltf, nodes, window_size)
        else:
            gl.glViewport(0, 0, window_size[0], window_size[1])
            gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
            for node in nodes:
                gltfu.draw_node(node, gltf,
                                projection_matrix=projection_matrix,
                                view_matrix=np.linalg.inv(world_matrix))
        if not stats_printed:
            print("num draw calls: %d" % gltfu.num_draw_calls)
            sys.stdout.flush()
            stats_printed = True
        glfw.SwapBuffers(window)

    if openvr:
        vr_renderer.shutdown()
    glfw.DestroyWindow(window)
    glfw.Terminate()


def main():    
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', help='path of glTF file to view')
    parser.add_argument("--openvr", help="view in VR (using OpenVR viewer)",
                        action="store_true")
    args = parser.parse_args()

    if args.openvr and OpenVRRenderer is None:
        raise Exception('error importing OpenVRRenderer')

    try:
        gltf = json.loads(open(args.filename).read())
        print('* loaded "%s"' % args.filename)
    except Exception as err:
        raise Exception('failed to load %s:\n%s' % (args.filename, err))

    gltf = JSobject(gltf)
    uri_path = os.path.dirname(args.filename)
    show_gltf(gltf, uri_path, openvr=args.openvr)


if __name__ == "__main__":
    main()
