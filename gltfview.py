import sys
import json
import os.path
import copy

import OpenGL.GL as gl
import OpenGL.GLU as glu

import cyglfw3 as glfw

import PIL.Image as Image


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
        # TODO: support data URIs
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


def setup_textures(gltf, gltf_dir):
    # TODO: support data URIs
    for image_name, image in gltf['images'].items():
        try:
            filename = os.path.join(gltf_dir, image['uri'])
            pil_image = Image.open(filename)
            print('* loaded image %s from %s' % (image_name, filename))
            image['pil_image'] = pil_image
        except Exception as err:
            print('* failed to load image %s:\n%s' % (image_name, err))
            exit(1)
    for texture_name, texture in gltf['textures'].items():
        texture_id = gl.glGenTextures(1)
        gl.glBindTexture(texture['target'], texture_id)
        image = gltf['images'][texture['source']]
        pil_image = image['pil_image']
        # following glview.cc example for now...
        gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
        pixel_format = gl.GL_RGB if image.get('component') == 3 else gl.GL_RGBA
        gl.glTexImage2D(texture['target'], 0, texture['internalFormat'],
                        pil_image.width, pil_image.height, 0,
                        pixel_format, texture['type'],
                        list(pil_image.getdata())) # TODO: better way to pass data?
        # gl.glTexParameterf(texture['target'], gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        # gl.glTexParameterf(texture['target'], gl.GL_TEXTURE_MAX_FILTER, gl.GL_LINEAR)
        if gl.glGetError() != gl.GL_NO_ERROR:
            print('* failed to create texture %s' % texture_name)
            exit(1)
        else:
            print('* created texture %s' % texture_name)
            texture['texture_id'] = texture_id
        gl.glBindTexture(texture['target'], 0)


def setup_buffers(gltf, gltf_dir):
    pass


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
    setup_textures(gltf, gltf_dir)
    setup_buffers(gltf, gltf_dir)

    display_gltf(window, gltf)
