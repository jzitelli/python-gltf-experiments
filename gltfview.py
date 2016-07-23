import sys
import json
import os.path
import copy

import OpenGL.GL as gl
import OpenGL.GLU as glu

import cyglfw3 as glfw

import PIL.Image as Image


ATTRIBUTE_TYPE_SIZES = {
    'SCALAR': 1,
    'VEC2': 2,
    'VEC3': 3,
    'VEC4': 4,
    'MAT2': 4,
    'MAT3': 9,
    'MAT4': 16
}


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
        program['id'] = program_id
        program['attribute_indices'] = {attribute: gl.glGetAttribLocation(program_id, attribute)
                                        for attribute in program['attributes']}
        print('* linked program %s' % program_name)
        print('  attribute indices: %s' % program['attribute_indices'])

        
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
    buffers = gltf['buffers']
    for buffer_name, buffer in buffers.items():
        # TODO: support data URIs
        try:
            filename = os.path.join(gltf_dir, buffer['uri'])
            buffer_data = None
            if buffer['type'] == 'arraybuffer':
                buffer_data = open(filename, 'rb').read()
            elif buffer['type'] == 'text':
                pass # TODO
            buffer['data'] = buffer_data
            print('* loaded buffer %s' % buffer_name)
        except Exception as err:
            print('* failed to load buffer %s:\n%s' % (buffer_name, err))
            exit(1)
    for bufferView_name, bufferView in gltf['bufferViews'].items():
        buffer_id = gl.glGenBuffers(1)
        byteOffset, byteLength = bufferView['byteOffset'], bufferView['byteLength']
        gl.glBindBuffer(bufferView['target'], buffer_id)
        gl.glBufferData(bufferView['target'], bufferView['byteLength'],
                        buffers[bufferView['buffer']]['data'][byteOffset:byteOffset+byteLength], gl.GL_STATIC_DRAW)
        if gl.glGetError() != gl.GL_NO_ERROR:
            print('* failed to create buffer %s' % bufferView_name)
            exit(1)
        else:
            print('* created buffer %s' % bufferView_name)
            bufferView['buffer_id'] = buffer_id
        gl.glBindBuffer(bufferView['target'], 0)


def draw_primitive(primitive, gltf):
    accessors = gltf['accessors']
    bufferViews = gltf['bufferViews']
    index_accessor = accessors[primitive['indices']]
    index_bufferView = bufferViews[index_accessor['bufferView']]
    gl.glBindBuffer(index_bufferView['target'], index_bufferView['buffer_id'])
    material = gltf['materials'][primitive['material']]
    technique = gltf['techniques'][material['technique']]
    program = gltf['programs'][technique['program']]
    gl.glUseProgram(program['id'])
    attribute_indices = program['attribute_indices']
    for semantic, accessor_name in primitive['attributes'].items():
        accessor = accessors[accessor_name]
        bufferView = bufferViews[accessor['bufferView']]
        buffer_id = bufferView['buffer_id']
        gl.glBindBuffer(bufferView['target'], buffer_id)
        # attribute_index = attribute_indices[technique['attributes'][tattribute]]
        # gl.glVertexAttribPointer(attribute_index, ATTRIBUTE_TYPE_SIZES[accessor['type']],
        #                          accessor['componentType'], False, accessor['byteStride'], accessor['byteOffset'])
        # gl.glEnableVertexAttribArray(attribute_index)

        
def display_gltf(window, gltf, scene=None):
    if scene is None:
        scene = gltf['scenes'][gltf['scene']]

    # testing >>>>>>
    mesh = list(gltf['meshes'].values())[0]
    primitive = mesh['primitives'][0]
    # main loop:
    while not glfw.WindowShouldClose(window):
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        draw_primitive(primitive, gltf)
        glfw.SwapBuffers(window)
        glfw.PollEvents()
    # <<<<<< testing

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
