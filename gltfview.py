import json

import OpenGL.GL as gl
import glfw3 as glfw

def main():
    window_size = (640, 480)
    window = glfw.CreateWindow(window_size[0], window_size[1], "gltfview")
    if not window:
        glfw.Terminate()
        print('failed to create glfw window')
        exit(1)
    # press ESC to quit:
    def keydown_callback(window, key, scancode, action, mods):
        if (key == glfw.KEY_ESCAPE and action == glfw.PRESS):
            glfw.SetWindowShouldClose(window, gl.GL_TRUE)
    glfw.SetKeyCallback(window, keydown_callback)
    # gl setup:
    glfw.MakeContextCurrent(window)
    print('OpenGL version: %s' % gl.glGetString(gl.GL_VERSION))
    gl.glViewport(0, 0, window_size[0], window_size[1])
    gl.glMatrixMode(gl.GL_PROJECTION)
    gl.glLoadIdentity()
    #gl.glPers
    # start main loop:
    while not glfw.WindowShouldClose(window):
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        glfw.SwapBuffers(window)
        glfw.PollEvents()
    # cleanup:
    print('quiting...')
    glfw.DestroyWindow(window)
    glfw.Terminate()


if __name__ == "__main__":
    if not glfw.Init():
        print('failed to initialize glfw')
    else:
        main()
