import sys
import json
import os.path
from ctypes import c_void_p, c_float, c_uint, sizeof, c_char_p
import base64

import OpenGL.GL as gl
import OpenGL.GLU as glu

import cyglfw3 as glfw

import PIL.Image as Image

import numpy as np

try: # python 3.3 or later
    from types import MappingProxyType
except ImportError as err:
    MappingProxyType = dict


class JSobject(dict):
    """Object-based representation (rather than dict) of JSON data.
    Useful for interactively exploring JSON data via ipython tab-completion."""
    def __init__(self, json_dict):
        dict.__init__(self)
        d = {}
        for k, v in json_dict.items():
            if k in self.__dict__:
                raise Exception('attribute name collision: %s' % k)
            if isinstance(v, dict):
                d[k] = JSobject(v)
            else:
                d[k] = v
        self.__dict__.update(d)
        self.update(d)


GLTF_BUFFERVIEW_TYPE_SIZES = MappingProxyType({
    'SCALAR': 1,
    'VEC2': 2,
    'VEC3': 3,
    'VEC4': 4,
    'MAT2': 4,
    'MAT3': 9,
    'MAT4': 16
})


def setup_glfw(width=900, height=600):
    if not glfw.Init():
        print('* failed to initialize glfw')
        sys.exit(1)
    window = glfw.CreateWindow(width, height, "gltfview")
    if not window:
        glfw.Terminate()
        print('* failed to create glfw window')
        sys.exit(1)
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


def calc_ortho_matrix(left=-10, right=10, bottom=-10, top=10, znear=0.1, zfar=1000):
    dx = right - left
    dy = top - bottom
    dz = zfar - znear
    rx = -(right + left) / (right - left)
    ry = -(top + bottom) / (top - bottom)
    rz = -(zfar + znear) / (zfar - znear)
    return np.array([[2.0/dx, 0,            0, rx],
                     [0,      2.0/dy,       0, ry],
                     [0,      0,      -2.0/dz, rz],
                     [0,      0,            0,  1]])


def calc_projection_matrix(yfov=np.pi/3, aspectRatio=1.5, znear=0.1, zfar=1000, **kwargs):
    f = 1 / np.tan(yfov / 2)
    return np.array([[f / aspectRatio, 0, 0, 0],
                     [0, f, 0, 0],
                     [0, 0, -(znear + zfar) / (znear - zfar), -2 * znear * zfar / (znear - zfar)],
                     [0, 0, -1, 0]])


def setup_shaders(gltf, uri_path):
    for shader_name, shader in gltf['shaders'].items():
        uri = shader['uri']
        if uri.startswith('data:text/plain;base64,'):
            shader_str = base64.b64decode(uri.split(',')[1])
        else:
            try:
                filename = os.path.join(uri_path, shader['uri'])
                shader_str = open(filename).read()
                print('* loaded shader "%s" (from %s):\n%s' % (shader_name, filename, shader_str))
            except Exception as err:
                print('* failed to load shader "%s":\n%s' % (shader_name, err))
                sys.exit(1)
        shader_id = gl.glCreateShader(shader['type'])
        gl.glShaderSource(shader_id, shader_str)
        gl.glCompileShader(shader_id)
        if not gl.glGetShaderiv(shader_id, gl.GL_COMPILE_STATUS):
            print('* failed to compile shader "%s"' % shader_name)
            sys.exit(1)
        print('* compiled shader "%s"' % shader_name)
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
            print('* failed to link program "%s"' % program_name)
            sys.exit(1)
        program['id'] = program_id
        program['attribute_locations'] = {attribute_name: gl.glGetAttribLocation(program_id, attribute_name)
                                        for attribute_name in program['attributes']}
        print('* linked program "%s"' % program_name)
        print('  attribute locations: %s' % program['attribute_locations'])


def setup_textures(gltf, uri_path):
    # TODO: support data URIs
    pil_images = {}
    for image_name, image in gltf.get('images', {}).items():
        try:
            filename = os.path.join(uri_path, image['uri'])
            pil_image = Image.open(filename)
            pil_images[image_name] = pil_image
            print('* loaded image "%s" (from %s)' % (image_name, filename))
        except Exception as err:
            print('* failed to load image "%s":\n%s' % (image_name, err))
            sys.exit(1)
    for texture_name, texture in gltf.get('textures', {}).items():
        sampler = gltf['samplers'][texture['sampler']]
        texture_id = gl.glGenTextures(1)
        #gl.glActiveTexture(gl.GL_TEXTURE0+0)
        gl.glBindTexture(texture['target'], texture_id)
        # following glview.cc example for now...
        # gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
        pixel_format = gl.GL_RGB if image.get('component') == 3 else gl.GL_RGBA
        gl.glTexParameterf(texture['target'], gl.GL_TEXTURE_MIN_FILTER, sampler.get('minFilter', 9986))
        gl.glTexParameterf(texture['target'], gl.GL_TEXTURE_MAG_FILTER, sampler.get('magFilter', 9729))
        gl.glTexParameterf(texture['target'], gl.GL_TEXTURE_WRAP_S, sampler.get('wrapS', 10497))
        gl.glTexParameterf(texture['target'], gl.GL_TEXTURE_WRAP_T, sampler.get('wrapT', 10497))
        # gl.glTexImage2D(texture['target'], 0, pixel_format,
        #                 pil_image.width, pil_image.height, 0,
        #                 pixel_format, gl.GL_UNSIGNED_BYTE,
        #                 list(pil_image.getdata())) # TODO: better way to pass data?
        gl.glTexImage2D(texture['target'], 0, texture['internalFormat'],
                        pil_image.width, pil_image.height, 0,
                        texture['format'], texture['type'],
                        list(pil_image.getdata())) # TODO: better way to pass data?
        sampler_id = gl.glGenSamplers(1)
        gl.glSamplerParameteri(sampler_id, gl.GL_TEXTURE_MIN_FILTER, sampler.get('minFilter', 9986))
        gl.glSamplerParameteri(sampler_id, gl.GL_TEXTURE_MAG_FILTER, sampler.get('magFilter', 9729))
        gl.glSamplerParameteri(sampler_id, gl.GL_TEXTURE_WRAP_S, sampler.get('wrapS', 10497))
        gl.glSamplerParameteri(sampler_id, gl.GL_TEXTURE_WRAP_T, sampler.get('wrapT', 10497))
        sampler['id'] = sampler_id
        gl.glGenerateMipmap(texture['target'])
        if gl.glGetError() != gl.GL_NO_ERROR:
            print('* failed to create texture "%s"' % texture_name)
            sys.exit(1)
        texture['id'] = texture_id
        #gl.glBindTexture(texture['target'], 0)
        print('* created texture "%s"' % texture_name)


def setup_buffers(gltf, uri_path):
    buffers = gltf['buffers']
    data_buffers = {}
    for buffer_name, buffer in buffers.items():
        uri = buffer['uri']
        if uri.startswith('data:application/octet-stream;base64,'):
            data_buffers[buffer_name] = base64.b64decode(uri.split(',')[1])
        else:
            try:
                filename = os.path.join(uri_path, buffer['uri'])
                if buffer['type'] == 'arraybuffer':
                    data_buffers[buffer_name] = open(filename, 'rb').read()
                    #data_buffers[buffer_name] = np.frombuffer(open(filename, 'rb').read(), dtype=np.float64)
                elif buffer['type'] == 'text':
                    pass # TODO
                print('* loaded buffer "%s" (from %s)' % (buffer_name, filename))
            except Exception as err:
                print('* failed to load buffer "%s":\n%s' % (buffer_name, err))
                sys.exit(1)
    for bufferView_name, bufferView in gltf['bufferViews'].items():
        buffer_id = gl.glGenBuffers(1)
        byteOffset, byteLength = bufferView['byteOffset'], bufferView['byteLength']
        gl.glBindBuffer(bufferView['target'], buffer_id)
        gl.glBufferData(bufferView['target'], bufferView['byteLength'],
                        data_buffers[bufferView['buffer']][byteOffset:], gl.GL_STATIC_DRAW)
        if gl.glGetError() != gl.GL_NO_ERROR:
            print('* failed to create buffer "%s"' % bufferView_name)
            sys.exit(1)
        bufferView['id'] = buffer_id
        gl.glBindBuffer(bufferView['target'], 0)
        print('* created buffer "%s"' % bufferView_name)


def setup_program_state(primitive, gltf,
                        modelview_matrix=None, projection_matrix=None, view_matrix=None):
    material = gltf['materials'][primitive['material']]
    technique = gltf['techniques'][material['technique']]
    program = gltf['programs'][technique['program']]
    accessors = gltf['accessors']
    bufferViews = gltf['bufferViews']
    textures = gltf.get('textures', {})
    samplers = gltf.get('samplers', {})
    for state in technique.get('states', {'enable': []})['enable']:
        gl.glEnable(state)
    gl.glUseProgram(program['id'])
    normal_matrix = np.ascontiguousarray(np.linalg.inv(modelview_matrix).T[:3, :3])
    material_values = material.get('values', {})
    for uniform_name, parameter_name in technique['uniforms'].items():
        parameter = technique['parameters'][parameter_name]
        location = gl.glGetUniformLocation(program['id'], uniform_name)
        if 'semantic' in parameter:
            if parameter['semantic'] == 'MODELVIEW':
                if 'node' in parameter:
                    world_matrix = gltf['nodes'][parameter['node']]['world_matrix']
                    gl.glUniformMatrix4fv(location, 1, True, np.ascontiguousarray(view_matrix.dot(world_matrix)))
                else:
                    gl.glUniformMatrix4fv(location, 1, True, np.ascontiguousarray(modelview_matrix))
            elif parameter['semantic'] == 'PROJECTION':
                if 'node' in parameter:
                    raise Exception()
                else:
                    gl.glUniformMatrix4fv(location, 1, True, np.ascontiguousarray(projection_matrix))
            elif parameter['semantic'] == 'MODELVIEWINVERSETRANSPOSE':
                if 'node' in parameter:
                    raise Exception()
                else:
                    gl.glUniformMatrix3fv(location, 1, True, normal_matrix)
            else:
                raise Exception('unhandled semantic: %s' % parameter['semantic'])
        else:
            value = material_values.get(parameter_name, parameter.get('value'))
            if value:
                if parameter['type'] == gl.GL_SAMPLER_2D:
                    texture = textures[value]
                    gl.glActiveTexture(gl.GL_TEXTURE0+0)
                    gl.glBindTexture(texture['target'], texture['id'])
                    gl.glBindSampler(0, samplers[texture['sampler']]['id'])
                    gl.glUniform1i(location, 0)
                elif parameter['type'] == gl.GL_FLOAT:
                    gl.glUniform1f(location, value)
                elif parameter['type'] == gl.GL_FLOAT_VEC2:
                    gl.glUniform2f(location, *value)
                elif parameter['type'] == gl.GL_FLOAT_VEC3:
                    gl.glUniform3f(location, *value)
                elif parameter['type'] == gl.GL_FLOAT_VEC4:
                    gl.glUniform4f(location, *value)
                else:
                    raise Exception('* unhandled type: %s' % parameter['type'])
            else:
                raise Exception('no value provided')
    for attribute_name, parameter_name in technique['attributes'].items():
        parameter = technique['parameters'][parameter_name]
        semantic = parameter.get('semantic')
        if semantic:
            accessor = accessors[primitive['attributes'][semantic]]
            bufferView = bufferViews[accessor['bufferView']]
            buffer_id = bufferView['id']
            location = program['attribute_locations'][attribute_name]
            gl.glEnableVertexAttribArray(location)
            gl.glBindBuffer(bufferView['target'], buffer_id)
            gl.glVertexAttribPointer(location, GLTF_BUFFERVIEW_TYPE_SIZES[accessor['type']],
                                     accessor['componentType'], False, accessor['byteStride'], c_void_p(accessor['byteOffset']))
            setup_program_state.enabled_locations.append(location)
        else:
            raise Exception()
setup_program_state.enabled_locations = []


def end_program_state():
    for loc in setup_program_state.enabled_locations:
        gl.glDisableVertexAttribArray(loc)
    setup_program_state.enabled_locations = []


def draw_primitive(primitive, gltf,
                   modelview_matrix=None, projection_matrix=None, view_matrix=None):
    accessors = gltf['accessors']
    bufferViews = gltf['bufferViews']
    setup_program_state(primitive, gltf,
                        modelview_matrix=modelview_matrix, projection_matrix=projection_matrix, view_matrix=view_matrix)
    index_accessor = accessors[primitive['indices']]
    index_bufferView = bufferViews[index_accessor['bufferView']]
    gl.glBindBuffer(index_bufferView['target'], index_bufferView['id'])
    gl.glDrawElements(primitive['mode'], index_accessor['count'], index_accessor['componentType'],
                      c_void_p(index_accessor['byteOffset']))
                      #None)
    if gl.glGetError() != gl.GL_NO_ERROR:
        print('* error drawing elements')
        sys.exit(1)
    end_program_state()


def draw_mesh(mesh, gltf,
              modelview_matrix=None, projection_matrix=None, view_matrix=None):
    for primitive in mesh['primitives']:
        draw_primitive(primitive, gltf,
                       modelview_matrix=modelview_matrix, projection_matrix=projection_matrix, view_matrix=view_matrix)


def draw_node(node, gltf,
              projection_matrix=None, view_matrix=None):
    if view_matrix is None:
        modelview_matrix = node['world_matrix']
    else:
        modelview_matrix = view_matrix.dot(node['world_matrix'])
    meshes = node.get('meshes', [])
    for mesh_name in meshes:
        draw_mesh(gltf['meshes'][mesh_name], gltf,
                  modelview_matrix=modelview_matrix, projection_matrix=projection_matrix, view_matrix=view_matrix)
    for child in node['children']:
        draw_node(gltf['nodes'][child], gltf,
                  projection_matrix=projection_matrix, view_matrix=view_matrix)


def update_world_matrices(node, gltf, world_matrix=None):
    matrix = np.array(node['matrix']).reshape((4, 4)).T
    if world_matrix is None:
        world_matrix = matrix
    else:
        world_matrix = world_matrix.dot(matrix)
    node['world_matrix'] = world_matrix
    for child in [gltf['nodes'][n] for n in node['children']]:
        update_world_matrices(child, gltf, world_matrix=world_matrix)


def render_scene(scene, gltf):
    nodes = [gltf['nodes'][n] for n in scene['nodes']]
    for node in nodes:
        update_world_matrices(node, gltf)
    #projection_matrix = calc_ortho_matrix(-20, 20, -15, 15, 0.1, 100)
    projection_matrix = calc_projection_matrix(aspectRatio=1.5, yfov=np.pi/3)
    view_matrix = np.eye(4)
    view_matrix[0, 3] = 20
    #view_matrix[1, 3] = -5
    view_matrix[2, 3] = -100
    for node in nodes:
        if 'camera' in node:
            projection_matrix = calc_projection_matrix(**gltf['cameras'][node['camera']])
            view_matrix = np.linalg.inv(node['world_matrix'])
            break
    for node in nodes:
        draw_node(node, gltf,
                  projection_matrix=projection_matrix, view_matrix=view_matrix)


def show_gltf(gltf, uri_path, scene_name=None):
    if scene_name is None:
        scene_name = gltf['scene']
    scene = gltf['scenes'][scene_name]
    window = setup_glfw()

    setup_shaders(gltf, uri_path)
    setup_programs(gltf)
    setup_textures(gltf, uri_path)
    setup_buffers(gltf, uri_path)

    sys.stdout.flush()

    gl.glClearColor(0.1, 0.2, 0.3, 1.0);

    # testing >>>>>>
    while not glfw.WindowShouldClose(window):
        glfw.PollEvents()
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT);
        render_scene(scene, gltf)
        glfw.SwapBuffers(window)
    # <<<<<< testing

    # cleanup:
    print('* closing window...')
    glfw.DestroyWindow(window)
    glfw.Terminate()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print('usage: python %s <path to gltf file>' % sys.argv[0])
        sys.exit()

    gltf = None
    try:
        gltf = json.loads(open(sys.argv[1]).read())
        print('* loaded %s' % sys.argv[1])
    except Exception as err:
        print('* failed to load %s:\n%s' % (sys.argv[1], err))
        sys.exit(1)

    uri_path = os.path.dirname(sys.argv[1])
    show_gltf(gltf, uri_path)

    gltf = JSobject(gltf)
    scene = gltf.scenes[gltf.scene]
    nodes = [gltf.nodes[n] for n in scene.nodes]
