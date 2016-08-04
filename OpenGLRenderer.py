import numpy as np

import OpenGL.GL as gl
import cyglfw3 as glfw

from glutils import *


class OpenGLRenderer(object):
    def __init__(self, window_size=(800, 600)):
        if not glfw.Init():
            raise Exception('failed to initialize glfw')
        width, height = window_size
        window = glfw.CreateWindow(width, height, "OpenGLRenderer")
        if not window:
            glfw.Terminate()
            raise Exception('failed to create glfw window')
        # set up glfw callbacks:
        def on_resize(window, width, height):
            # TODO: update projection matrix
            gl.glViewport(0, 0, width, height)
        glfw.SetWindowSizeCallback(window, on_resize)
        def on_keydown(window, key, scancode, action, mods):
            if (key == glfw.KEY_ESCAPE and action == glfw.PRESS):
                glfw.SetWindowShouldClose(window, True)
        glfw.SetKeyCallback(window, on_keydown)
        glfw.MakeContextCurrent(window)
        print('GL_VERSION: %s' % gl.glGetString(gl.GL_VERSION))
        on_resize(window, width, height)
        self.window = window
        self.window_size = window_size
    def render(self, scene, view_matrix=None, projection_matrix=None):
        pass
    def start_render_loop(self):
        while not glfw.WindowShouldClose(self.window):
            glfw.PollEvents()
            gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
            # render ...
            glfw.SwapBuffers(self.window)
        print('* closing window...')
        glfw.DestroyWindow(self.window)
        glfw.Terminate()
        

if __name__ == '__main__':
    renderer = OpenGLRenderer()
    renderer.start_render_loop()
