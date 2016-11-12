import os.path
import base64
from ctypes import c_void_p
try: # python 3.3 or later
    from types import MappingProxyType
except ImportError as err:
    MappingProxyType = dict

import numpy as np
import OpenGL.GL as gl
import PIL.Image as Image
from pyrr import matrix44


CHECK_GL_ERRORS = False

GLTF_BUFFERVIEW_TYPE_SIZES = MappingProxyType({
    'SCALAR': 1,
    'VEC2': 2,
    'VEC3': 3,
    'VEC4': 4,
    'MAT2': 4,
    'MAT3': 9,
    'MAT4': 16
})


def setup_shaders(gltf, uri_path):
    """Loads and compiles all shaders defined or referenced in the given gltf."""
    shader_ids = {}
    for shader_name, shader in gltf['shaders'].items():
        uri = shader['uri']
        if uri.startswith('data:text/plain;base64,'):
            shader_str = base64.urlsafe_b64decode(uri.split(',')[1]).decode()
            print('* decoded shader "%s":\n%s' % (shader_name, shader_str))
        else:
            filename = os.path.join(uri_path, shader['uri'])
            shader_str = open(filename).read()
            print('* loaded shader "%s" (from %s):\n%s' % (shader_name, filename, shader_str))
        shader_id = gl.glCreateShader(shader['type'])
        gl.glShaderSource(shader_id, shader_str)
        gl.glCompileShader(shader_id)
        if not gl.glGetShaderiv(shader_id, gl.GL_COMPILE_STATUS):
            raise Exception('failed to compile shader "%s":\n%s' % (shader_name, gl.glGetShaderInfoLog(shader_id).decode()))
        print('* compiled shader "%s"' % shader_name)
        #shader['id'] = shader_id
        shader_ids[shader_name] = shader_id
    return shader_ids


def setup_programs(gltf, shader_ids):
    shaders = gltf['shaders']
    for program_name, program in gltf['programs'].items():
        program_id = gl.glCreateProgram()
        gl.glAttachShader(program_id, shader_ids[program['vertexShader']])
        gl.glAttachShader(program_id, shader_ids[program['fragmentShader']])
        gl.glLinkProgram(program_id)
        gl.glDetachShader(program_id, shader_ids[program['vertexShader']])
        gl.glDetachShader(program_id, shader_ids[program['fragmentShader']])
        if not gl.glGetProgramiv(program_id, gl.GL_LINK_STATUS):
            raise Exception('failed to link program "%s"' % program_name)
        program['id'] = program_id
        program['attribute_locations'] = {attribute_name: gl.glGetAttribLocation(program_id, attribute_name)
                                          for attribute_name in program['attributes']}
        program['uniform_locations'] = {}
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
                        gl.GL_RGB, #texture['format'], # INVESTIGATE
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


def set_technique_state(technique_name, gltf):
    if set_technique_state.current_technique is not None and set_technique_state.current_technique == technique_name:
        return
    set_technique_state.current_technique = technique_name
    technique = gltf['techniques'][technique_name]
    program = gltf['programs'][technique['program']]
    gl.glUseProgram(program['id'])
    enabled_states = technique.get('states', {}).get('enable', [])
    for state, is_enabled in list(set_technique_state.states.items()):
        if state in enabled_states:
            if not is_enabled:
                gl.glEnable(state)
                set_technique_state.states[state] = True
        elif is_enabled:
            gl.glDisable(state)
            set_technique_state.states[state] = False
    for state in enabled_states:
        if state not in set_technique_state.states:
            gl.glEnable(state)
            set_technique_state.states[state] = True
set_technique_state.current_technique = None
set_technique_state.states = {}


def set_material_state(material_name, gltf):
    if set_material_state.current_material == material_name:
        return
    set_material_state.current_material = material_name
    material = gltf['materials'][material_name]
    set_technique_state(material['technique'], gltf)
    technique = gltf['techniques'][material['technique']]
    program = gltf['programs'][technique['program']]
    textures = gltf.get('textures', {})
    samplers = gltf.get('samplers', {})
    material_values = material.get('values', {})
    for uniform_name, parameter_name in technique['uniforms'].items():
        parameter = technique['parameters'][parameter_name]
        if 'semantic' in parameter:
            continue
        value = material_values.get(parameter_name, parameter.get('value'))
        if value:
            if uniform_name in program['uniform_locations']:
                location = program['uniform_locations'][uniform_name]
            else:
                location = gl.glGetUniformLocation(program['id'], uniform_name)
                program['uniform_locations'][uniform_name] = location
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
    if CHECK_GL_ERRORS:
        if gl.glGetError() != gl.GL_NO_ERROR:
            raise Exception('error setting material state')
set_material_state.current_material = None


def set_draw_state(primitive, gltf,
                   modelview_matrix=None,
                   projection_matrix=None,
                   view_matrix=None,
                   normal_matrix=None):
    set_material_state(primitive['material'], gltf)
    material = gltf['materials'][primitive['material']]
    technique = gltf['techniques'][material['technique']]
    program = gltf['programs'][technique['program']]
    accessors = gltf['accessors']
    bufferViews = gltf['bufferViews']
    accessor_names = primitive['attributes']
    set_draw_state.enabled_locations = []
    buffer_id = None
    for attribute_name, parameter_name in technique['attributes'].items():
        parameter = technique['parameters'][parameter_name]
        if 'semantic' in parameter:
            semantic = parameter['semantic']
            if semantic in accessor_names:
                accessor = accessors[accessor_names[semantic]]
                bufferView = bufferViews[accessor['bufferView']]
                location = program['attribute_locations'][attribute_name]
                gl.glEnableVertexAttribArray(location)
                if buffer_id != bufferView['id']:
                    buffer_id = bufferView['id']
                    gl.glBindBuffer(bufferView['target'], buffer_id)
                gl.glVertexAttribPointer(location, GLTF_BUFFERVIEW_TYPE_SIZES[accessor['type']],
                                         accessor['componentType'], False, accessor['byteStride'], c_void_p(accessor['byteOffset']))
                set_draw_state.enabled_locations.append(location)
        else:
            raise Exception('expected a semantic property for attribute "%s"' % attribute_name)
    for uniform_name, parameter_name in technique['uniforms'].items():
        parameter = technique['parameters'][parameter_name]
        if 'semantic' in parameter:
            location = gl.glGetUniformLocation(program['id'], uniform_name)
            if parameter['semantic'] == 'MODELVIEW':
                if 'node' in parameter and view_matrix is not None:
                    world_matrix = gltf['nodes'][parameter['node']]['world_matrix']
                    world_matrix.dot(view_matrix, out=set_draw_state.modelview_matrix)
                    gl.glUniformMatrix4fv(location, 1, False, set_draw_state.modelview_matrix)
                elif modelview_matrix is not None:
                    gl.glUniformMatrix4fv(location, 1, False, modelview_matrix)
            elif parameter['semantic'] == 'PROJECTION':
                if 'node' in parameter:
                    raise Exception('TODO')
                elif projection_matrix is not None:
                    gl.glUniformMatrix4fv(location, 1, False, projection_matrix)
            elif parameter['semantic'] == 'MODELVIEWINVERSETRANSPOSE':
                if 'node' in parameter:
                    raise Exception('TODO')
                elif normal_matrix is not None:
                    gl.glUniformMatrix3fv(location, 1, True, normal_matrix)
            else:
                raise Exception('unhandled semantic: %s' % parameter['semantic'])
    if CHECK_GL_ERRORS:
        if gl.glGetError() != gl.GL_NO_ERROR:
            raise Exception('error setting draw state')
set_draw_state.modelview_matrix = np.empty((4,4), dtype=np.float32)
set_draw_state.enabled_locations = []


def draw_primitive(primitive, gltf,
                   modelview_matrix=None,
                   projection_matrix=None,
                   view_matrix=None,
                   normal_matrix=None):
    set_draw_state(primitive, gltf,
                   modelview_matrix=modelview_matrix,
                   projection_matrix=projection_matrix,
                   view_matrix=view_matrix,
                   normal_matrix=normal_matrix)
    index_accessor = gltf['accessors'][primitive['indices']]
    index_bufferView = gltf['bufferViews'][index_accessor['bufferView']]
    gl.glBindBuffer(index_bufferView['target'], index_bufferView['id'])
    gl.glDrawElements(primitive['mode'], index_accessor['count'], index_accessor['componentType'],
                      c_void_p(index_accessor['byteOffset']))
    global num_draw_calls
    num_draw_calls += 1
    if CHECK_GL_ERRORS:
        if gl.glGetError() != gl.GL_NO_ERROR:
            raise Exception('error drawing elements')
    for loc in set_draw_state.enabled_locations:
        gl.glDisableVertexAttribArray(loc)
    set_draw_state.enabled_locations = []
num_draw_calls = 0


def draw_mesh(mesh, gltf,
              modelview_matrix=None,
              projection_matrix=None,
              view_matrix=None,
              normal_matrix=None):
    for i, primitive in enumerate(mesh['primitives']):
        draw_primitive(primitive, gltf,
                       modelview_matrix=(modelview_matrix if i == 0 else None),
                       projection_matrix=(projection_matrix if i == 0 else None),
                       view_matrix=(view_matrix if i == 0 else None),
                       normal_matrix=(normal_matrix if i == 0 else None))


def draw_node(node, gltf,
              projection_matrix=None, view_matrix=None):
    node['world_matrix'].dot(view_matrix, out=draw_node.modelview_matrix)
    normal_matrix = np.linalg.inv(draw_node.modelview_matrix[:3,:3])
    meshes = node.get('meshes', [])
    for mesh_name in meshes:
        draw_mesh(gltf['meshes'][mesh_name], gltf,
                  modelview_matrix=draw_node.modelview_matrix,
                  projection_matrix=projection_matrix, view_matrix=view_matrix, normal_matrix=normal_matrix)
    for child in node['children']:
        draw_node(gltf['nodes'][child], gltf,
                  projection_matrix=projection_matrix, view_matrix=view_matrix)
draw_node.modelview_matrix = np.empty((4,4), dtype=np.float32)


def update_world_matrices(node, gltf, world_matrix=None):
    if 'matrix' not in node:
        matrix = matrix44.create_from_quaternion(np.array(node['rotation']))
        matrix[:3, 0] *= node['scale'][0]
        matrix[:3, 1] *= node['scale'][1]
        matrix[:3, 2] *= node['scale'][2]
        matrix[:3, 3] = node['translation']
    else:
        matrix = np.array(node['matrix'], dtype=np.float32).reshape((4, 4)).T
    if world_matrix is None:
        world_matrix = matrix
    else:
        world_matrix = world_matrix.dot(matrix)
    node['world_matrix'] = world_matrix.T
    for child in [gltf['nodes'][n] for n in node['children']]:
        update_world_matrices(child, gltf, world_matrix=world_matrix)
