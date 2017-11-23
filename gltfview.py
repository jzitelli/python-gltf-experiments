import sys
import os.path
import json
import argparse
import functools
from collections import defaultdict
import logging

import numpy as np

import OpenGL
OpenGL.ERROR_CHECKING = False
OpenGL.ERROR_LOGGING = False
OpenGL.ERROR_ON_COPY = True
import OpenGL.GL as gl

import cyglfw3 as glfw

from pyrr import matrix44


_logger = logging.getLogger(__name__)
import gltfutils as gltfu
from jsobject import JSobject as jsobject
try:
    from OpenVRRenderer import OpenVRRenderer
except ImportError:
    OpenVRRenderer = None
# from gltext import TextDrawer


LOGGING_FORMAT =       '[gltfview.py] %(asctime)s * %(levelname)s * %(name)s : %(message)s'
DEBUG_LOGGING_FORMAT = '[gltfview.py] %(asctime)s * %(levelname)s * %(name)s : %(message)s'


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
    _logger.info('GL_VERSION: %s' % gl.glGetString(gl.GL_VERSION))
    return window


def view_gltf(gltf, uri_path, scene_name=None, openvr=False, window_size=None):
    if scene_name is None:
        scene_name = gltf['scene']
    if window_size is None:
        window_size = [800, 600]
    window = setup_glfw(width=window_size[0], height=window_size[1],
                        double_buffered=not openvr)
    def on_resize(window, width, height):
        window_size[0], window_size[1] = width, height
    glfw.SetWindowSizeCallback(window, on_resize)
    if openvr and OpenVRRenderer is not None:
        vr_renderer = OpenVRRenderer()
    # text_drawer = TextDrawer()

    gl.glClearColor(0.01, 0.01, 0.17, 1.0);

    shader_ids = gltfu.setup_shaders(gltf, uri_path)
    gltfu.setup_programs(gltf, shader_ids)
    gltfu.setup_textures(gltf, uri_path)
    gltfu.setup_buffers(gltf, uri_path)

    scene = gltf.scenes[scene_name]
    nodes = [gltf.nodes[n] for n in scene.nodes]
    for node in nodes:
        gltfu.update_world_matrices(node, gltf)

    camera_world_matrix = np.eye(4, dtype=np.float32)
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
    camera_position = camera_world_matrix[3, :3]
    camera_rotation = camera_world_matrix[:3, :3]
    dposition = np.zeros(3, dtype=np.float32)
    rotation = np.eye(3, dtype=np.float32)

    key_state = defaultdict(bool)

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

    move_speed = 2.0
    turn_speed = 0.5

    def process_input(dt):
        glfw.PollEvents()
        dposition[:] = 0.0
        if key_state[glfw.KEY_W]:
            dposition[2] -= dt * move_speed
        if key_state[glfw.KEY_S]:
            dposition[2] += dt * move_speed
        if key_state[glfw.KEY_A]:
            dposition[0] -= dt * move_speed
        if key_state[glfw.KEY_D]:
            dposition[0] += dt * move_speed
        if key_state[glfw.KEY_Q]:
            dposition[1] += dt * move_speed
        if key_state[glfw.KEY_Z]:
            dposition[1] -= dt * move_speed
        theta = 0.0
        if key_state[glfw.KEY_LEFT]:
            theta -= dt * turn_speed
        if key_state[glfw.KEY_RIGHT]:
            theta += dt * turn_speed
        rotation[0,0] = np.cos(theta)
        rotation[2,2] = rotation[0,0]
        rotation[0,2] = np.sin(theta)
        rotation[2,0] = -rotation[0,2]
        camera_rotation[...] = rotation.dot(camera_world_matrix[:3,:3])
        camera_position[:] += camera_rotation.T.dot(dposition)

    # sort nodes from front to back to avoid overdraw (assuming opaque objects):
    nodes = sorted(nodes, key=lambda node: np.linalg.norm(camera_position - node['world_matrix'][3, :3]))

    _logger.info('starting render loop...')
    sys.stdout.flush()
    gltfu.num_draw_calls = 0
    nframes = 0
    lt = glfw.GetTime()
    dt_max = 0.0
    while not glfw.WindowShouldClose(window):
        t = glfw.GetTime()
        dt = t - lt
        dt_max = max(dt, dt_max)
        lt = t
        process_input(dt)
        if openvr:
            vr_renderer.process_input()
            vr_renderer.render(gltf, nodes, window_size)
        else:
            gl.glViewport(0, 0, window_size[0], window_size[1])
            gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
            view_matrix = np.linalg.inv(camera_world_matrix)
            gltfu.set_material_state.current_material = None
            gltfu.set_technique_state.current_technique = None
            for node in nodes:
                gltfu.draw_node(node, gltf,
                                projection_matrix=projection_matrix,
                                view_matrix=view_matrix)
            # text_drawer.draw_text("%f" % dt, color=(1.0, 1.0, 0.0, 0.0),
            #                       view_matrix=view_matrix,
            #                       projection_matrix=projection_matrix)
        if nframes == 0:
            _logger.info("num draw calls per frame: %d", gltfu.num_draw_calls)
            sys.stdout.flush()
            gltfu.num_draw_calls = 0
            st = glfw.GetTime()
        nframes += 1
        glfw.SwapBuffers(window)
    _logger.info('FPS (avg): %f', ((nframes - 1) / (t - st)))
    _logger.info('MAX FRAME RENDER TIME: %f', dt_max)
    sys.stdout.flush()

    if openvr:
        vr_renderer.shutdown()
    glfw.DestroyWindow(window)
    glfw.Terminate()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', help='path of glTF file to view')
    parser.add_argument("--openvr", help="view in VR", action="store_true")
    parser.add_argument("-v", help="enable verbose logging", action="store_true")

    args = parser.parse_args()
    if args.v:
        logging.basicConfig(format=DEBUG_LOGGING_FORMAT, level=logging.DEBUG)
    else:
        logging.basicConfig(format=LOGGING_FORMAT, level=logging.WARNING)
    if args.openvr and OpenVRRenderer is None:
        raise Exception('error importing OpenVRRenderer')

    global gltf
    try:
        gltf = json.loads(open(args.filename).read())
        _logger.info('* loaded "%s"', args.filename)
    except Exception as err:
        raise Exception('failed to load %s:\n%s' % (args.filename, err))

    # for prop in DEFAULT_GLTF.keys():
    #     gltf[prop].update(DEFAULT_GLTF[prop])

    gltf = jsobject(gltf)
    uri_path = os.path.dirname(args.filename)

    view_gltf(gltf, uri_path, openvr=args.openvr)

    global view
    view = functools.partial(view_gltf, gltf, uri_path, openvr=args.openvr)


if __name__ == "__main__":
    main()
