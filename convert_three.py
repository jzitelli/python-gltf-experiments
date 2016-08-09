import argparse
import json
import os

import jsonschema


GLTF_SCHEMA_ROOT = os.path.join(os.path.split(__file__)[0], 'schema')
GLTF_SCHEMAS = {}
for filename in os.listdir(GLTF_SCHEMA_ROOT):
    if filename.endswith('.schema.json'):
        with open(os.path.join(GLTF_SCHEMA_ROOT, filename)) as f:
            GLTF_SCHEMAS[filename[:-len('.schema.json')]] = json.loads(f.read())

            
def convert_three(three_json):
    gltf = {prop_name: prop_spec['default']
            for prop_name, prop_spec in GLTF_SCHEMAS['glTF']['properties'].items()
            if 'default' in prop_spec}
    return gltf


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='path to input file')
    args = parser.parse_args()

    with open(args.input) as f:
        json_str = f.read()
    three_json = json.loads(json_str)

    gltf = convert_three(three_json)
    
