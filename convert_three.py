import argparse
import json
import os
import base64

import numpy as np

import pyrr


GLTF_SCHEMA_ROOT = os.path.join(os.path.split(__file__)[0], 'schema')
GLTF_SCHEMAS = {}
for filename in os.listdir(GLTF_SCHEMA_ROOT):
    if filename.endswith('.schema.json'):
        with open(os.path.join(GLTF_SCHEMA_ROOT, filename)) as f:
            GLTF_SCHEMAS[filename[:-len('.schema.json')]] = json.loads(f.read())


def convert_three(three_json):
    three_object = three_json['object']
    if three_object['type'] != 'Scene':
        raise Exception('expected a "Scene" object type instead of "%s"' % three_object['type'])

    def make_default(gltf_type):
        return {prop_name: prop_spec['default']
                for prop_name, prop_spec in GLTF_SCHEMAS[gltf_type]['properties'].items()
                if 'default' in prop_spec}

    gltf = make_default('glTF')
    gltf['scene'] = three_object.get('name',
                                     three_object['uuid'])

    def convert_geometry(geom):
        if geom['type'] == 'BufferGeometry':
            data = geom['data']
            for attr_name, attr in data['attributes'].items():
                buffer_bytes = np.array(attr['array']).tobytes()
                attr_buffer = {'type': 'text',
                               'uri': 'data:application/octet-stream;base64,%s' % base64.urlsafe_b64encode(buffer_bytes)} # TODO: fix
                attr_buffer_id = '%s: %s' % (geom['uuid'], attr_name)
                gltf['buffers'][attr_buffer_id] = attr_buffer
                attr_bufferView = {'buffer': attr_buffer_id,
                                   'byteOffset': 0,
                                   'byteLength': len(buffer_bytes),
                                   'target': 34962} # ARRAY_BUFFER
                gltf['bufferViews'][attr_buffer_id] = attr_bufferView
                attr_accessor = {}

    for geom in three_json['geometries']:
        convert_geometry(geom)

    def convert_image(image):
        pass

    for image in three_json.get('images', []):
        convert_image(image)

    def convert_texture(tex):
        pass
    
    for tex in three_json.get('textures', []):
        convert_texture(tex)
        
    def convert_material(mat):
        pass

    for mat in three_json['materials']:
        convert_material(mat)
    
    def convert_object(obj):
        node = {'name': obj.get('name',
                                obj['uuid']),
                'children': []}
        gltf['nodes'][node['name']] = node
        if 'matrix' in obj:
            node['matrix'] = list(obj['matrix'])
        else:
            node['translation'] = list(obj['position'])
            node['quaternion'] = list(obj.get('quaternion',
                                              pyrr.quaternion.create_from_eulers(obj['rotation'])))
            node['scale'] = list(obj['scale'])
        for child in obj['children']:
            node['children'].append(convert_object(child))
        if obj['type'] == 'Mesh':
            pass
        elif obj['type'] == 'PerspectiveCamera':
            camera = {'type': 'perspective',
                      'perspective': {'yfov': obj['fov'],
                                      'aspectRatio': obj['aspect'],
                                      'znear': obj['near'],
                                      'zfar': obj['far']}}
            node['camera'] = obj['name']
            gltf['cameras'][node['camera']] = camera
        elif obj['type'] == 'OrthographicCamera':
            raise Exception('TODO')
        elif obj['type'] == 'DirectionalLight':
            raise Exception('TODO')
        elif obj['type'] == 'Scene':
            pass
        elif obj['type'] != 'Object3D':
            raise Exception('unexpected object type: "%s"' % obj['type'])
        return node['name']

    gltf['scenes'][gltf['scene']] = {'nodes': [convert_object(three_object)]}
    return gltf


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='path to input file')
    args = parser.parse_args()

    with open(args.input) as f:
        json_str = f.read()
    three_json = json.loads(json_str)
    gltf = convert_three(three_json)
