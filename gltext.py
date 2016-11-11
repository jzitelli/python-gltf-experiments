import os.path

import OpenGL.GL as gl
import PIL.Image as Image


_vertex_shader = """precision highp float;
uniform mat4 u_modelViewMatrix;
uniform mat4 u_projectionMatrix;
attribute vec3 a_position;
attribute vec2 a_texcoord0;
varying vec2 v_texcoord0;
void main(void) {
  vec4 pos = u_modelViewMatrix * vec4(a_position,1.0);
  v_texcoord0 = a_texcoord0;
  gl_Position = u_projectionMatrix * pos;
}"""


_fragment_shader = """precision highp float;
uniform sampler2D u_fonttex;
uniform vec4 u_color;
varying vec2 v_texcoord0;
void main(void) {
  gl_FragColor = u_color * texture2D(u_fonttex, v_texcoord0);
}"""


DEFAULT_FONT_IMAGE = os.path.join(os.path.split(os.path.abspath(__file__))[0], 'stb_font_consolas_32_usascii.png')


class TextDrawer(object):
    def __init__(self, font_image=DEFAULT_FONT_IMAGE):
        image = Image.open(font_image)
        vs_id = gl.glCreateShader(gl.GL_VERTEX_SHADER)
        gl.glShaderSource(vs_id, _vertex_shader)
        gl.glCompileShader(vs_id)
        if not gl.glGetShaderiv(vs_id, gl.GL_COMPILE_STATUS):
            raise Exception('failed to compile gltext vertex shader:\n%s' % gl.glGetShaderInfoLog(vs_id).decode())
        fs_id = gl.glCreateShader(gl.GL_FRAGMENT_SHADER)
        gl.glShaderSource(fs_id, _fragment_shader)
        gl.glCompileShader(fs_id)
        if not gl.glGetShaderiv(fs_id, gl.GL_COMPILE_STATUS):
            raise Exception('failed to compile gltext fragment shader:\n%s' % gl.glGetShaderInfoLog(fs_id).decode())
        program_id = gl.glCreateProgram()
        gl.glAttachShader(program_id, vs_id)
        gl.glAttachShader(program_id, fs_id)
        gl.glLinkProgram(program_id)
        gl.glDetachShader(program_id, vs_id)
        gl.glDetachShader(program_id, fs_id)
        if not gl.glGetProgramiv(program_id, gl.GL_LINK_STATUS):
            raise Exception('failed to link gltext program')
    def draw_text(self, text, position=(0,0), scale=1, color=(1.0, 1.0, 1.0, 1.0)):
        pass
