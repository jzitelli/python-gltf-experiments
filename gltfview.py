import sys
import json
import os.path
from ctypes import c_void_p
import base64

import OpenGL.GL as gl

import cyglfw3 as glfw

import PIL.Image as Image

import numpy as np


from glutils import *
from gltfutils import *


def setup_glfw(width=900, height=600):
    if not glfw.Init():
        raise Exception('failed to initialize glfw')
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


def setup_shaders(gltf, uri_path):
    for shader_name, shader in gltf['shaders'].items():
        uri = shader['uri']
        if uri.startswith('data:text/plain;base64,'):
            shader_str = base64.b64decode(uri.split(',')[1])
        else:
            filename = os.path.join(uri_path, shader['uri'])
            shader_str = open(filename).read()
            print('* loaded shader "%s" (from %s):\n%s' % (shader_name, filename, shader_str))
        shader_id = gl.glCreateShader(shader['type'])
        gl.glShaderSource(shader_id, shader_str)
        gl.glCompileShader(shader_id)
        if not gl.glGetShaderiv(shader_id, gl.GL_COMPILE_STATUS):
            raise Exception('failed to compile shader "%s"' % shader_name)
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
            raise Exception('failed to link program "%s"' % program_name)
        program['id'] = program_id
        program['attribute_locations'] = {attribute_name: gl.glGetAttribLocation(program_id, attribute_name)
                                        for attribute_name in program['attributes']}
        print('* linked program "%s"' % program_name)
        print('  attribute locations: %s' % program['attribute_locations'])


def setup_textures(gltf, uri_path):
    # TODO: support data URIs
    pil_images = {}
    for image_name, image in gltf.get('images', {}).items():
        filename = os.path.join(uri_path, image['uri'])
        pil_image = Image.open(filename)
        pil_images[image_name] = pil_image
        print('* loaded image "%s" (from %s)' % (image_name, filename))
    for texture_name, texture in gltf.get('textures', {}).items():
        sampler = gltf['samplers'][texture['sampler']]
        texture_id = gl.glGenTextures(1)
        gl.glBindTexture(texture['target'], texture_id)
        sampler_id = gl.glGenSamplers(1)
        gl.glSamplerParameteri(sampler_id, gl.GL_TEXTURE_MIN_FILTER, sampler.get('minFilter', 9986))
        gl.glSamplerParameteri(sampler_id, gl.GL_TEXTURE_MAG_FILTER, sampler.get('magFilter', 9729))
        gl.glSamplerParameteri(sampler_id, gl.GL_TEXTURE_WRAP_S, sampler.get('wrapS', 10497))
        gl.glSamplerParameteri(sampler_id, gl.GL_TEXTURE_WRAP_T, sampler.get('wrapT', 10497))
        sampler['id'] = sampler_id
        gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
        if texture['type'] != gl.GL_UNSIGNED_BYTE:
            raise Exception('TODO')
        gl.glTexImage2D(texture['target'], 0,
                        texture['internalFormat'],
                        pil_image.width, pil_image.height, 0,
                        gl.GL_RGB, #texture['format'],
                        texture['type'],
                        np.array(list(pil_image.getdata()), dtype=(np.ubyte if texture['type'] == gl.GL_UNSIGNED_BYTE else np.ushort)))
        gl.glGenerateMipmap(texture['target'])
        if gl.glGetError() != gl.GL_NO_ERROR:
            raise Exception('failed to create texture "%s"' % texture_name)
        texture['id'] = texture_id
        print('* created texture "%s"' % texture_name)


def setup_buffers(gltf, uri_path):
    buffers = gltf['buffers']
    data_buffers = {}
    for buffer_name, buffer in buffers.items():
        uri = buffer['uri']
        if uri.startswith('data:application/octet-stream;base64,'):
            data_buffers[buffer_name] = base64.b64decode(uri.split(',')[1])
        else:
            filename = os.path.join(uri_path, buffer['uri'])
            if buffer['type'] == 'arraybuffer':
                data_buffers[buffer_name] = open(filename, 'rb').read()
            elif buffer['type'] == 'text':
                raise Exception('TODO')
                #data_buffers[buffer_name] = open(filename, 'r').read()
            print('* loaded buffer "%s" (from %s)' % (buffer_name, filename))
    for bufferView_name, bufferView in gltf['bufferViews'].items():
        buffer_id = gl.glGenBuffers(1)
        byteOffset, byteLength = bufferView['byteOffset'], bufferView['byteLength']
        gl.glBindBuffer(bufferView['target'], buffer_id)
        gl.glBufferData(bufferView['target'], bufferView['byteLength'],
                        data_buffers[bufferView['buffer']][byteOffset:], gl.GL_STATIC_DRAW)
        if gl.glGetError() != gl.GL_NO_ERROR:
            raise Exception('failed to create buffer "%s"' % bufferView_name)
        bufferView['id'] = buffer_id
        gl.glBindBuffer(bufferView['target'], 0)
        print('* created buffer "%s"' % bufferView_name)


def setup_program_state(primitive, gltf,
                        modelview_matrix=None, projection_matrix=None, view_matrix=None, normal_matrix=None):
    material = gltf['materials'][primitive['material']]
    technique = gltf['techniques'][material['technique']]
    program = gltf['programs'][technique['program']]
    accessors = gltf['accessors']
    bufferViews = gltf['bufferViews']
    textures = gltf.get('textures', {})
    samplers = gltf.get('samplers', {})
    gl.glUseProgram(program['id'])
    setup_program_state.enabled_states = technique.get('states', {}).get('enable', setup_program_state.enabled_states)
    for state in setup_program_state.enabled_states:
        gl.glEnable(state)
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
                    raise Exception('TODO')
                else:
                    gl.glUniformMatrix4fv(location, 1, True, np.ascontiguousarray(projection_matrix))
            elif parameter['semantic'] == 'MODELVIEWINVERSETRANSPOSE':
                if 'node' in parameter:
                    raise Exception('TODO')
                else:
                    gl.glUniformMatrix3fv(location, 1, True, np.ascontiguousarray(normal_matrix))
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
                    raise Exception('unhandled parameter type: %s' % parameter['type'])
            else:
                raise Exception('no value provided for parameter "%s"' % parameter_name)
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
            raise Exception('expected a semantic property for attribute "%s"' % attribute_name)
setup_program_state.enabled_locations = []
setup_program_state.enabled_states = []


def end_program_state():
    for loc in setup_program_state.enabled_locations:
        gl.glDisableVertexAttribArray(loc)
    setup_program_state.enabled_locations = []
    for state in setup_program_state.enabled_states:
        gl.glDisable(state)
    setup_program_state.enabled_states = []

def draw_primitive(primitive, gltf,
                   modelview_matrix=None, projection_matrix=None, view_matrix=None, normal_matrix=None):
    accessors = gltf['accessors']
    bufferViews = gltf['bufferViews']
    setup_program_state(primitive, gltf,
                        modelview_matrix=modelview_matrix, projection_matrix=projection_matrix, view_matrix=view_matrix, normal_matrix=normal_matrix)
    index_accessor = accessors[primitive['indices']]
    index_bufferView = bufferViews[index_accessor['bufferView']]
    gl.glBindBuffer(index_bufferView['target'], index_bufferView['id'])
    gl.glDrawElements(primitive['mode'], index_accessor['count'], index_accessor['componentType'],
                      c_void_p(index_accessor['byteOffset']))
                      #None)
    if gl.glGetError() != gl.GL_NO_ERROR:
        raise Exception('error drawing elements')
    end_program_state()


def draw_mesh(mesh, gltf,
              modelview_matrix=None, projection_matrix=None, view_matrix=None, normal_matrix=None):
    for primitive in mesh['primitives']:
        draw_primitive(primitive, gltf,
                       modelview_matrix=modelview_matrix, projection_matrix=projection_matrix, view_matrix=view_matrix, normal_matrix=normal_matrix)


def draw_node(node, gltf,
              projection_matrix=None, view_matrix=None):
    if view_matrix is None:
        modelview_matrix = node['world_matrix']
    else:
        modelview_matrix = view_matrix.dot(node['world_matrix'])
    normal_matrix = np.linalg.inv(modelview_matrix[:3,:3]).T
    meshes = node.get('meshes', [])
    for mesh_name in meshes:
        draw_mesh(gltf['meshes'][mesh_name], gltf,
                  modelview_matrix=modelview_matrix, projection_matrix=projection_matrix, view_matrix=view_matrix, normal_matrix=normal_matrix)
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


def render_scene(scene, gltf, projection_matrix=None, view_matrix=None):
    nodes = [gltf['nodes'][n] for n in scene['nodes']]
    for node in nodes:
        update_world_matrices(node, gltf)
    for node in nodes:
        if 'camera' in node:
            projection_matrix = calc_projection_matrix(**gltf['cameras'][node['camera']])
            view_matrix = np.linalg.inv(node['world_matrix'])
            break
    if projection_matrix is None:
        projection_matrix = calc_projection_matrix(aspectRatio=1.5, yfov=np.pi/2.5)
    if view_matrix is None:
        view_matrix = np.eye(4)
        view_matrix[2, 3] = -15
    for node in nodes:
        draw_node(node, gltf,
                  projection_matrix=projection_matrix, view_matrix=view_matrix)


def show_gltf(gltf, uri_path, scene_name=None):
    if scene_name is None:
        scene_name = gltf['scene']
    scene = gltf['scenes'][scene_name]
    window = setup_glfw()

    gl.glClearColor(0.1, 0.2, 0.3, 1.0);

    setup_shaders(gltf, uri_path)
    setup_programs(gltf)
    setup_textures(gltf, uri_path)
    setup_buffers(gltf, uri_path)

    sys.stdout.flush()

    while not glfw.WindowShouldClose(window):
        glfw.PollEvents()
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT);
        render_scene(scene, gltf)
        glfw.SwapBuffers(window)

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
        raise Exception('failed to load %s:\n%s' % (sys.argv[1], err))

    uri_path = os.path.dirname(sys.argv[1])

    gltf = JSobject(gltf)

    show_gltf(gltf, uri_path)

    scene = gltf.scenes[gltf.scene]
    nodes = [gltf.nodes[n] for n in scene.nodes]
