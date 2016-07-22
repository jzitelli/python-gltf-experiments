import sys
import json
import os.path

import OpenGL.GL as gl
import OpenGL.GLU as glu

import cyglfw3 as glfw


def display_gltf(window, gltf, scene=None):
    if scene is None:
        scene = gltf['scenes'][gltf['scene']]
    # setup programs:
    for program_name, program in gltf['programs'].items():
        # load shaders from URIs:
        vshader_name = program['vertexShader']
        vshader = gltf['shaders'][vshader_name]
        vshader_str = None
        if 'uri' in vshader:
            try:
                vshader_str = open(os.path.join(os.path.dirname(sys.argv[1]), vshader['uri'])).read()
                print('loaded vertex shader %s:\n%s' % (vshader_name, vshader_str))
            except Exception as err:
                print('failed to open vertex shader %s:\n%s' % (vshader_name, err))
                exit(1)
        fshader_name = program['fragmentShader']
        fshader = gltf['shaders'][fshader_name]
        fshader_str = None
        if 'uri' in fshader:
            try:
                fshader_str = open(os.path.join(os.path.dirname(sys.argv[1]), fshader['uri'])).read()
                print('loaded fragment shader %s:\n%s' % (fshader_name, fshader_str))
            except Exception as err:
                print('failed to open fragment shader %s:\n%s' % (fshader_name, err))
                exit(1)
        # compile shaders:
        vshader_id = gl.glCreateShader(gl.GL_VERTEX_SHADER)
        gl.glShaderSource(vshader_id, vshader_str)
        gl.glCompileShader(vshader_id)
        if not gl.glGetShaderiv(vshader_id, gl.GL_COMPILE_STATUS):
            print('failed to compile vertex shader %s' % vshader_name)
            exit(1)
        else:
            print('compiled vertex shader %s' % vshader_name)
        fshader_id = gl.glCreateShader(gl.GL_FRAGMENT_SHADER)
        gl.glShaderSource(fshader_id, fshader_str)
        gl.glCompileShader(fshader_id)
        if not gl.glGetShaderiv(fshader_id, gl.GL_COMPILE_STATUS):
            print('failed to compile fragment shader %s' % fshader_name)
            exit(1)
        else:
            print('compiled fragment shader %s' % fshader_name)
        program_id = gl.glCreateProgram()
        gl.glAttachShader(program_id, vshader_id)
        gl.glAttachShader(program_id, fshader_id)
        gl.glLinkProgram(program_id)
        gl.glDetachShader(program_id, vshader_id)
        gl.glDetachShader(program_id, fshader_id)
        if not gl.glGetProgramiv(program_id, gl.GL_LINK_STATUS):
            print('failed to link program %s' % program_name)
            exit(1)
        else:
            print('linked program %s' % program_name)

    # main loop:
    while not glfw.WindowShouldClose(window):
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        glfw.SwapBuffers(window)
        glfw.PollEvents()
    # cleanup:
    print('quiting...')
    glfw.DestroyWindow(window)
    glfw.Terminate()


def setup_glfw():
    if not glfw.Init():
        print('failed to initialize glfw')
        exit(1)
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
    glfw.MakeContextCurrent(window)
    print('OpenGL version: %s' % gl.glGetString(gl.GL_VERSION))
    on_resize(window, window_size[0], window_size[1])
    return window


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print('usage: python %s <path to gltf file>' % sys.argv[0])
        exit()
    gltf = None
    try:
        gltf = json.loads(open(sys.argv[1]).read())
    except Exception as err:
        print('failed to load %s:\n%s' % (sys.argv[1], err))
        exit(1)
    print('loaded %s:\n%s' % (sys.argv[1], json.dumps(gltf, indent=2)))
    window = setup_glfw()
    display_gltf(window, gltf)
