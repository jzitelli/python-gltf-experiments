import sys
import json
import os.path
import copy

import OpenGL.GL as gl
import OpenGL.GLU as glu

import cyglfw3 as glfw


def setup_glfw(width=640, height=480):
    if not glfw.Init():
        print('* failed to initialize glfw')
        exit(1)
    window = glfw.CreateWindow(width, height, "gltfview")
    if not window:
        glfw.Terminate()
        print('* failed to create glfw window')
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
    print('GL_VERSION: %s' % gl.glGetString(gl.GL_VERSION))
    on_resize(window, width, height)
    return window


def setup_shaders(gltf, gltf_dir):
    for shader_name, shader in gltf['shaders'].items():
        # TODO: support embedded-data URI
        shader_str = None
        try:
            shader_str = open(os.path.join(gltf_dir, shader['uri'])).read()
            print('* loaded shader %s:\n%s' % (shader_name, shader_str))
        except Exception as err:
            print('* failed to load shader %s:\n%s' % (shader_name, err))
            exit(1)
        shader_id = gl.glCreateShader(shader['type'])
        gl.glShaderSource(shader_id, shader_str)
        gl.glCompileShader(shader_id)
        if not gl.glGetShaderiv(shader_id, gl.GL_COMPILE_STATUS):
            print('* failed to compile shader %s' % shader_name)
            exit(1)
        else:
            print('* compiled shader %s' % shader_name)
            shader['id'] = shader_id


def setup_programs(gltf):
    shaders = gltf['shaders']
    for program_name, program in gltf['programs'].items():
        program_id = gl.glCreateProgram()
        gl.glAttachShader(program_id, shaders[program['vertexShader']]['id'])
        gl.glAttachShader(program_id, shaders[program['fragmentShader']]['id'])
        gl.glLinkProgram(program_id)
        gl.glDetachShader(program_id, shaders[program['vertexShader']]['id'])
        gl.glDetachShader(program_id, shaders[program['fragmentShader']]['id'])
        if not gl.glGetProgramiv(program_id, gl.GL_LINK_STATUS):
            print('* failed to link program %s' % program_name)
            exit(1)
        else:
            print('* linked program %s' % program_name)
            program['id'] = program_id


def display_gltf(window, gltf, scene=None):
    if scene is None:
        scene = gltf['scenes'][gltf['scene']]
    # main loop:
    while not glfw.WindowShouldClose(window):
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        glfw.SwapBuffers(window)
        glfw.PollEvents()
    # cleanup:
    print('* quiting...')
    glfw.DestroyWindow(window)
    glfw.Terminate()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print('usage: python %s <path to gltf file>' % sys.argv[0])
        exit()

    gltf = None
    try:
        gltf = json.loads(open(sys.argv[1]).read())
        print('* loaded %s:\n%s' % (sys.argv[1], json.dumps(gltf, indent=2)))
    except Exception as err:
        print('* failed to load %s:\n%s' % (sys.argv[1], err))
        exit(1)
    gltf_dir = os.path.dirname(sys.argv[1])

    window = setup_glfw()

    setup_shaders(gltf, gltf_dir)
    setup_programs(gltf)

    display_gltf(window, gltf)
