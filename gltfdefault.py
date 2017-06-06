import json
import base64


DEFAULT_VS = b"""precision highp float;
uniform mat4 u_modelViewMatrix;
uniform mat4 u_projectionMatrix;
attribute vec3 a_position;
void main(void) {
    gl_Position = u_projectionMatrix * u_modelViewMatrix * vec4(a_position,1.0);
}"""
DEFAULT_VS_BASE64 = base64.b64encode(DEFAULT_VS).decode()


DEFAULT_FS = b"""precision highp float;
uniform vec4 u_emission;
void main(void) {
    gl_FragColor = u_emission;
}"""
DEFAULT_FS_BASE64 = base64.b64encode(DEFAULT_FS).decode()


DEFAULT_GLTF = json.loads("""{
"materials": {
    "Effect1": {
        "technique": "technique0"
    }
},
"programs": {
    "program0": {
        "attributes": [
            "a_position"
        ],
        "fragmentShader": "fragmentShader0",
        "vertexShader": "vertexShader0"
    }
},
"shaders": {
    "vertexShader0": {
        "type": 35633,
        "uri": "data:text/plain;base64,"
    },
    "fragmentShader0": {
        "type": 35632,
        "uri": "data:text/plain;base64,"
    }
},
"techniques": {
    "technique0": {
        "attributes": {
            "a_position": "position"
        },
        "parameters": {
            "modelViewMatrix": {
                "semantic": "MODELVIEW",
                "type": 35676
            },
            "projectionMatrix": {
                "semantic": "PROJECTION",
                "type": 35676
            },
            "emission": {
                "type": 35666,
                "value": [
                    0.5,
                    0.5,
                    0.5,
                    1
                ]
            },
            "position": {
                "semantic": "POSITION",
                "type": 35665
            }
        },
        "program": "program0",
        "states": {
            "enable": [
                2884,
                2929
            ]
        },
        "uniforms": {
            "u_modelViewMatrix": "modelViewMatrix",
            "u_projectionMatrix": "projectionMatrix",
            "u_emission": "emission"
        }
    }
}
}""")

DEFAULT_GLTF['shaders']['vertexShader0']['uri'] += DEFAULT_VS_BASE64
DEFAULT_GLTF['shaders']['fragmentShader0']['uri'] += DEFAULT_FS_BASE64

if __name__ == "__main__":
    with open('default.gltf', 'w') as f:
        f.write(json.dumps(DEFAULT_GLTF, indent=2))
