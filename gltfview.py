import sys
import os.path
import json
import argparse
import functools

import numpy as np

import OpenGL
OpenGL.ERROR_CHECKING = False
OpenGL.ERROR_LOGGING = False
OpenGL.ERROR_ON_COPY = True
import OpenGL.GL as gl

import cyglfw3 as glfw

from pyrr import matrix44


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


def view_gltf(gltf, uri_path, scene_name=None, openvr=False, window_size=None):
    if scene_name is None:
        scene_name = gltf['scene']
    if window_size is None:
        window_size = [800, 600]

    window = setup_glfw(width=window_size[0], height=window_size[1],
                        double_buffered=not openvr)

    if openvr and OpenVRRenderer is not None:
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

    for node in nodes:
        gltfu.update_world_matrices(node, gltf)

    camera_world_matrix = np.eye(4, 4, dtype=np.float32)
    view_matrix = np.linalg.inv(camera_world_matrix)
    projection_matrix = np.array(matrix44.create_perspective_projection_matrix(np.rad2deg(55), window_size[0]/window_size[1], 0.1, 1000),
                                 dtype=np.float32)
    for node in nodes:
        if 'camera' in node:
            camera = gltf['cameras'][node['camera']]
            if 'perspective' in camera:
                perspective = camera['perspective']
                projection_matrix = np.array(matrix44.create_perspective_projection_matrix(np.rad2deg(perspective['yfov']), perspective['aspectRatio'],
                                                                                           perspective['znear'], perspective['zfar']),
                                             dtype=np.float32)
            elif 'orthographic' in camera:
                raise Exception('TODO')
            camera_world_matrix = node['world_matrix']
            break

    key_state = {glfw.KEY_W: False,
                 glfw.KEY_S: False,
                 glfw.KEY_A: False,
                 glfw.KEY_D: False,
                 glfw.KEY_Q: False,
                 glfw.KEY_Z: False}
    def on_keydown(window, key, scancode, action, mods):
        if key == glfw.KEY_ESCAPE and action == glfw.PRESS:
            glfw.SetWindowShouldClose(window, gl.GL_TRUE)
        elif action == glfw.PRESS:
            key_state[key] = True
        elif action == glfw.RELEASE:
            key_state[key] = False
    glfw.SetKeyCallback(window, on_keydown)

    def on_mousedown(window, button, action, mods):
        pass
    glfw.SetMouseButtonCallback(window, on_mousedown)

    move_speed = 2

    def process_input(dt):
        glfw.PollEvents()
        if key_state[glfw.KEY_W]:
            camera_world_matrix[3,2] += dt * move_speed
        if key_state[glfw.KEY_S]:
            camera_world_matrix[3,2] -= dt * move_speed
        if key_state[glfw.KEY_A]:
            camera_world_matrix[3,0] += dt * move_speed
        if key_state[glfw.KEY_D]:
            camera_world_matrix[3,0] -= dt * move_speed
        if key_state[glfw.KEY_Q]:
            camera_world_matrix[3,1] += dt * move_speed
        if key_state[glfw.KEY_Z]:
            camera_world_matrix[3,1] -= dt * move_speed

    print('* starting render loop...')
    sys.stdout.flush()
    nframes = 0
    lt = glfw.GetTime()
    while not glfw.WindowShouldClose(window):
        t = glfw.GetTime()
        dt = t - lt
        lt = t
        process_input(dt)
        if openvr:
            vr_renderer.process_input()
            vr_renderer.render(gltf, nodes, window_size)
        else:
            gl.glViewport(0, 0, window_size[0], window_size[1])
            gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
            view_matrix = np.linalg.inv(camera_world_matrix)
            for node in nodes:
                gltfu.draw_node(node, gltf,
                                projection_matrix=projection_matrix,
                                view_matrix=view_matrix)
        if nframes == 0:
            print("* num draw calls per frame: %d" % gltfu.num_draw_calls)
            sys.stdout.flush()
            gltfu.num_draw_calls = 0
            st = glfw.GetTime()
        nframes += 1
        glfw.SwapBuffers(window)
    print('* FPS (avg): %f' % ((nframes - 1) / (t - st)))

    if openvr:
        vr_renderer.shutdown()
    glfw.DestroyWindow(window)
    glfw.Terminate()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', help='path of glTF file to view')
    parser.add_argument("--openvr", help="view in VR", action="store_true")
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
    view_gltf(gltf, uri_path, openvr=args.openvr)
    global view
    view = functools.partial(view_gltf, gltf, uri_path, openvr=args.openvr)


if __name__ == "__main__":
    main()
