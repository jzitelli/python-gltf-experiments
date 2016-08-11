import argparse
import json
import os
import base64
import re

import OpenGL.GL as gl

import numpy as np

import pyrr


GLTF_SCHEMA_ROOT = os.path.join(os.path.split(__file__)[0], 'schema')
GLTF_SCHEMAS = {}
for filename in os.listdir(GLTF_SCHEMA_ROOT):
    if filename.endswith('.schema.json'):
        with open(os.path.join(GLTF_SCHEMA_ROOT, filename)) as f:
            GLTF_SCHEMAS[filename[:-len('.schema.json')]] = json.loads(f.read())


THREE_SHADERS_ROOT = os.path.join(os.path.split(__file__)[0],
                                  os.path.pardir,
                                  'three.js', 'src', 'renderers', 'shaders')

THREE_SHADERCHUNK = {}
for filename in os.listdir(os.path.join(THREE_SHADERS_ROOT, 'ShaderChunk')):
    if filename.endswith('.glsl'):
        with open(os.path.join(THREE_SHADERS_ROOT, 'ShaderChunk', filename)) as f:
            THREE_SHADERCHUNK[filename[:-len('.glsl')]] = f.read()

THREE_SHADERLIB = {}
for filename in os.listdir(os.path.join(THREE_SHADERS_ROOT, 'ShaderLib')):
    if filename.endswith('.glsl'):
        with open(os.path.join(THREE_SHADERS_ROOT, 'ShaderLib', filename)) as f:
            THREE_SHADERLIB[filename[:-len('.glsl')]] = f.read()

VERTEX_PREFIX = '\n'.join(['#version 420',
                           'precision highp float;',
                           'precision highp int;',
                           'uniform mat4 modelMatrix;',
                           'uniform mat4 modelViewMatrix;',
                           'uniform mat4 projectionMatrix;',
                           'uniform mat4 viewMatrix;',
                           'uniform mat3 normalMatrix;',
                           'uniform vec3 cameraPosition;',
                           'attribute vec3 position;',
                           'attribute vec3 normal;',
                           'attribute vec2 uv;',
                           '#define FLAT_SHADED',
                           '#define NUM_CLIPPING_PLANES 0'])

FRAGMENT_PREFIX = '\n'.join(['#version 420',
                             'precision highp float;',
                             'precision highp int;',
                             'uniform mat4 viewMatrix;',
			     'uniform vec3 cameraPosition;',
                             '#define FLAT_SHADED',
                             '#define NUM_CLIPPING_PLANES 0',
                             'vec4 linearToOutputTexel( vec4 value ) { return value; }'])

for name, src in list(THREE_SHADERLIB.items()):
    m = re.search(r"#include +<(?P<shaderchunk>\w+)>", src)
    while m is not None:
        src = src.replace(m.group(0), THREE_SHADERCHUNK[m.group('shaderchunk')], 1)
        m = re.search(r" *#include +<(?P<shaderchunk>\w+)> *", src)
    if name.endswith('_vert'):
        src = '\n'.join([VERTEX_PREFIX, src])
    else:
        src = '\n'.join([FRAGMENT_PREFIX, src])
    THREE_SHADERLIB[name] = src


# TODO: support all shader variants yielded by #define permutations
SHADERS = {name: {'uri': 'data:text/plain;base64,%s' % base64.urlsafe_b64encode(bytes(src, 'utf-8')).decode('utf-8'),
                  'type': gl.GL_VERTEX_SHADER if name.endswith('_vert') else gl.GL_FRAGMENT_SHADER}
           for name, src in THREE_SHADERLIB.items()}


PROGRAMS = {
    'basic': {
        'attributes': ['position', 'normal', 'uv'],
        'fragmentShader': 'meshbasic_frag',
        'vertexShader': 'meshbasic_vert'
    }
}


TECHNIQUES = {
    'MeshBasicMaterial': {
        'program': 'basic',
        'parameters': {
            'position': {'type': gl.GL_FLOAT_VEC3,
                         'semantic': 'POSITION'},
            'normal': {'type': gl.GL_FLOAT_VEC3,
                       'semantic': 'NORMAL'},
            'uv': {'type': gl.GL_FLOAT_VEC2,
                   'semantic': 'TEXCOORD'},
            'modelViewMatrix': {'type': gl.GL_FLOAT_MAT4,
                                'semantic': 'MODELVIEW'},
            'modelMatrix': {'type': gl.GL_FLOAT_MAT4,
                            'semantic': 'MODEL'},
            'viewMatrix': {'type': gl.GL_FLOAT_MAT4,
                           'semantic': 'VIEW'},
            'normalMatrix': {'type': gl.GL_FLOAT_MAT3,
                             'semantic': 'MODELVIEWINVERSETRANSPOSE'},
            'projectionMatrix': {'type': gl.GL_FLOAT_MAT4,
                                 'semantic': 'PROJECTION'},
            'cameraPosition': {'type': gl.GL_FLOAT_VEC3},
            'diffuse': {'type': gl.GL_FLOAT_VEC3},
            'opacity': {'type': gl.GL_FLOAT}
        },
        'attributes': {glsl_name: glsl_name for glsl_name in PROGRAMS['basic']['attributes']},
        'uniforms': {glsl_name: glsl_name for glsl_name in ['modelMatrix', 'modelViewMatrix', 'projectionMatrix', 'viewMatrix', 'normalMatrix', 'cameraPosition', 'diffuse', 'opacity']},
        'states': {'enable': [gl.GL_DEPTH_TEST]}
    }
}


TYPED_ARRAY_GLTYPE = {
    'Int8Array':    5120,
    'Uint8Array':   5121,
    'Int16Array':   5122,
    'Uint16Array':  5123,
    'Float32Array': 5126
}


TYPED_ARRAY_DTYPE = {
    'Int8Array':    np.int8,
    'Uint8Array':   np.uint8,
    'Int16Array':   np.int16,
    'Uint16Array':  np.uint16,
    'Float32Array': np.float32
}


ITEMSIZE_MAP = {
    1: 'SCALAR',
    2: 'VEC2',
    3: 'VEC3',
    4: 'VEC4'
}


def convert_three(three_json):
    three_object = three_json['object']
    if three_object['type'] != 'Scene':
        raise Exception('expected a "Scene" object type instead of "%s"' % three_object['type'])

    def make_default(gltf_type):
        return {prop_name: prop_spec['default']
                for prop_name, prop_spec in GLTF_SCHEMAS[gltf_type]['properties'].items()
                if 'default' in prop_spec}

    gltf = make_default('glTF')

    def convert_geometry(geom):
        if geom['type'] == 'BufferGeometry':
            data = geom['data']
            for attr_name, attr in data['attributes'].items():
                buffer_bytes = np.array(attr['array'], dtype=TYPED_ARRAY_DTYPE[attr['type']]).tobytes()
                attr_buffer = {'type': 'text',
                               'uri': 'data:application/octet-stream;base64,%s' % base64.b64encode(buffer_bytes).decode('utf-8')}
                attr_buffer_id = '%s: %s' % (geom['uuid'], attr_name)
                gltf['buffers'][attr_buffer_id] = attr_buffer
                attr_bufferView = {'buffer': attr_buffer_id,
                                   'byteOffset': 0,
                                   'byteLength': len(buffer_bytes),
                                   'target': gl.GL_ARRAY_BUFFER}
                attr_bufferView_id = attr_buffer_id
                gltf['bufferViews'][attr_bufferView_id] = attr_bufferView
                attr_accessor = {'bufferView': attr_bufferView_id,
                                 'byteOffset': 0,
                                 'byteStride': 0,
                                 'componentType': TYPED_ARRAY_GLTYPE[attr['type']],
                                 'count': len(attr['array']) // attr['itemSize'],
                                 'type': ITEMSIZE_MAP[attr['itemSize']]} # TODO: min/max properties?
                attr_accessor_id = attr_bufferView_id
                gltf['accessors'][attr_accessor_id] = attr_accessor
            index = data['index']
            index_buffer_bytes = np.array(index['array'], dtype=TYPED_ARRAY_DTYPE[index['type']]).tobytes()
            index_buffer = {'type': 'text',
                            'uri': 'data:application/octet-stream;base64,%s' % base64.b64encode(index_buffer_bytes).decode('utf-8')}
            index_buffer_id = '%s: index' % geom['uuid']
            gltf['buffers'][index_buffer_id] = index_buffer
            index_bufferView = {'buffer': index_buffer_id,
                                'byteOffset': 0,
                                'byteLength': len(index_buffer_bytes),
                                'target': gl.GL_ELEMENT_ARRAY_BUFFER}
            index_bufferView_id = index_buffer_id
            gltf['bufferViews'][index_bufferView_id] = index_bufferView
            index_accessor = {'bufferView': index_bufferView_id,
                              'byteOffset': 0,
                              'byteStride': 0,
                              'componentType': TYPED_ARRAY_GLTYPE[index['type']],
                              'count': len(index['array']),
                              'type': ITEMSIZE_MAP[index['itemSize']]}
            index_accessor_id = index_bufferView_id
            gltf['accessors'][index_accessor_id] = index_accessor
        else:
            pass # TODO

    for geom in three_json['geometries']:
        convert_geometry(geom)

    def convert_image(image):
        pass # TODO

    for image in three_json.get('images', []):
        convert_image(image)

    def convert_texture(tex):
        pass # TODO
    
    for tex in three_json.get('textures', []):
        convert_texture(tex)
        
    def convert_material(mat):
        if mat['type'] == 'MeshBasicMaterial':
            material = {'technique': 'MeshBasicMaterial',
                        'values': {}}
            values = material['values']
            if 'name' in mat:
                material['name'] = mat['name']
            if 'color' in mat:
                values['diffuse'] = [1.0, 0, 0] # TODO
            material_id = mat['uuid']
            gltf['materials'][material_id] = material
            technique = TECHNIQUES['MeshBasicMaterial']
            gltf['techniques']['MeshBasicMaterial'] = technique
            program_id = technique['program']
            program = PROGRAMS[program_id]
            gltf['programs'][program_id] = program
            gltf['shaders'][program['vertexShader']] = SHADERS[program['vertexShader']]
            gltf['shaders'][program['fragmentShader']] = SHADERS[program['fragmentShader']]

    for mat in three_json['materials']:
        convert_material(mat)

    three_geometries = {geom['uuid']: geom for geom in three_json['geometries']}
    
    def convert_object(obj):
        node = {'children': []}
        if 'name' in obj:
            node['name'] = obj['name']
        node_id = obj['uuid']
        gltf['nodes'][node_id] = node
        if 'matrix' in obj:
            node['matrix'] = list(obj['matrix'])
        else:
            node['translation'] = list(obj['position'])
            node['rotation'] = list(obj.get('quaternion',
                                            pyrr.quaternion.create_from_eulers(obj['rotation'])))
            node['scale'] = list(obj['scale'])

        if obj['type'] == 'Mesh':
            mesh_id = obj['geometry']
            mat_id = obj['material']
            geom = three_geometries[mesh_id]
            if geom['type'] == 'BufferGeometry':
                data = geom['data']
                primitive = {
                    'attributes': {attr_name: '%s: %s' % (geom['uuid'], attr_name)
                                   for attr_name in data['attributes'].keys()},
                    'indices': '%s: index' % geom['uuid'],
                    'material': mat_id
                }
                primitive['mode'] = gl.GL_TRIANGLES
                mesh = {'primitives': [primitive]}
                node['meshes'] = [mesh_id]
                gltf['meshes'][mesh_id] = mesh
            else:
                pass # TODO
        elif obj['type'] == 'PerspectiveCamera':
            camera = {'type': 'perspective',
                      'perspective': {'yfov': obj['fov'],
                                      'aspectRatio': obj['aspect'],
                                      'znear': obj['near'],
                                      'zfar': obj['far']}}
            camera_id = obj['uuid']
            node['camera'] = camera_id
            gltf['cameras'][camera_id] = camera
        elif obj['type'] == 'OrthographicCamera':
            raise Exception('TODO')
        elif obj['type'] == 'DirectionalLight':
            raise Exception('TODO')
        elif obj['type'] == 'Scene':
            pass
        elif obj['type'] != 'Object3D':
            raise Exception('unexpected object type: "%s"' % obj['type'])

        for child in obj['children']:
            node['children'].append(convert_object(child))
        return node_id

    scene = {'nodes': [convert_object(three_object)]}
    gltf['scene'] = three_object.get('name',
                                     three_object['uuid'])
    gltf['scenes'][gltf['scene']] = scene
    return gltf


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='path to input file')
    args = parser.parse_args()

    with open(args.input) as f:
        json_str = f.read()
    three_json = json.loads(json_str)
    gltf = convert_three(three_json)
    output = '%s.gltf' % args.input[:-len('.json')]
    with open(output, 'w') as f:
        f.write(json.dumps(gltf, indent=2, sort_keys=True))
        print('wrote "%s"' % output)
