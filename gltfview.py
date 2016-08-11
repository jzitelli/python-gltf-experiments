import sys
import os.path
import json
import argparse

import OpenGL
OpenGL.ERROR_CHECKING = False
OpenGL.ERROR_LOGGING = False
OpenGL.ERROR_ON_COPY = True
import OpenGL.GL as gl

import cyglfw3 as glfw


import gltfutils as gltfu
from JSobject import JSobject


def setup_glfw(width=900, height=600, double_buffered=False):
    if not glfw.Init():
        raise Exception('failed to initialize glfw')
    if not double_buffered:
        glfw.WindowHint(glfw.DOUBLEBUFFER, False)
        glfw.SwapInterval(0)
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


def show_gltf(gltf, uri_path, scene_name=None):
    if scene_name is None:
        scene_name = gltf['scene']
    scene = gltf['scenes'][scene_name]
    window = setup_glfw()

    try:
        gl.glClearColor(0.1, 0.2, 0.3, 1.0);

        renderer = Renderer()
        renderer.set_scene(gltf, uri_path, gltf.scene)

        print('* starting render loop...')
        sys.stdout.flush()

        while not glfw.WindowShouldClose(window):
            glfw.PollEvents()
            renderer.render()
            glfw.SwapBuffers(window)

        del renderer
    finally:
        glfw.DestroyWindow(window)
        glfw.Terminate()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', help='path of glTF file to view')
    parser.add_argument("--openvr", help="view in VR (using OpenVR viewer)",
                        action="store_true")
    args = parser.parse_args()

    if args.openvr:
        from OpenVRRenderer import OpenVRRenderer as Renderer
    else:
        from OpenGLRenderer import OpenGLRenderer as Renderer

    uri_path = os.path.dirname(args.filename)
    gltf = None
    try:
        gltf = json.loads(open(args.filename).read())
        print('* loaded "%s"' % args.filename)
    except Exception as err:
        raise Exception('failed to load %s:\n%s' % (args.filename, err))
    gltf = JSobject(gltf)

    show_gltf(gltf, uri_path)
