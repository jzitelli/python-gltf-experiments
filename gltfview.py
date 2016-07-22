import sys
import json

import OpenGL.GL as gl
import OpenGL.GLU as glu
import glfw3 as glfw

def main():
    window_size = (640, 480)
    window = glfw.CreateWindow(window_size[0], window_size[1], "gltfview")
    if not window:
        glfw.Terminate()
        print('failed to create glfw window')
        exit(1)

    # set up glfw callbacks:
    def on_resize(window, width, height):
        gl.glViewport(0, 0, width, height)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        glu.gluPerspective(50, float(width) / height, 0.1, 1000)
        gl.glMatrixMode(gl.GL_MODELVIEW)
    glfw.SetWindowSizeCallback(window, on_resize)
    def on_keydown(window, key, scancode, action, mods):
        # press ESC to quit:
        if (key == glfw.KEY_ESCAPE and action == glfw.PRESS):
            glfw.SetWindowShouldClose(window, gl.GL_TRUE)
    glfw.SetKeyCallback(window, on_keydown)

    # gl setup:
    glfw.MakeContextCurrent(window)
    print('OpenGL version: %s' % gl.glGetString(gl.GL_VERSION))
    on_resize(window, window_size[0], window_size[1])

    # main loop:
    while not glfw.WindowShouldClose(window):
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        glfw.SwapBuffers(window)
        glfw.PollEvents()

    # cleanup:
    print('quiting...')
    glfw.DestroyWindow(window)
    glfw.Terminate()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print('usage: python %s <path to gltf file>' % sys.argv[0])
        exit()
    if not glfw.Init():
        print('failed to initialize glfw')
        exit(1)
    main()
