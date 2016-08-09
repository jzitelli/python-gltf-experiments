import argparse
import json
import os

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
        raise Exception('unexpected object type: "%s"' % three_object['type'])
    three_geometries = three_json['geometries']
    three_materials = three_json['materials']
    three_textures = three_json.get('textures', [])
    three_images = three_json.get('images', [])
    def make_default(gltf_type):
        return {prop_name: prop_spec['default']
                for prop_name, prop_spec in GLTF_SCHEMAS[gltf_type]['properties'].items()
                if 'default' in prop_spec}
    # gltf = {prop_name: prop_spec['default']
    #         for prop_name, prop_spec in GLTF_SCHEMAS['glTF']['properties'].items()
    #         if 'default' in prop_spec}
    gltf = make_default('glTF')
    gltf['scene'] = three_object.get('name',
                                     three_object['uuid'])
    
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
            camera = {'perspective': {'yfov': obj['fov'],
                                      'aspectRatio': obj['aspect'],
                                      'znear': obj['near'],
                                      'zfar': obj['far']}}
            gltf['cameras'][obj['name']] = camera
        elif obj['type'] == 'OrthographicCamera':
            pass
        elif obj['type'] == 'DirectionalLight':
            pass
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
