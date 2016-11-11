import os.path

import numpy as np
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
        texture_id = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
        sampler_id = gl.glGenSamplers(1)
        gl.glSamplerParameteri(sampler_id, gl.GL_TEXTURE_MIN_FILTER, 9986)
        gl.glSamplerParameteri(sampler_id, gl.GL_TEXTURE_MAG_FILTER, 9729)
        gl.glSamplerParameteri(sampler_id, gl.GL_TEXTURE_WRAP_S, 10497)
        gl.glSamplerParameteri(sampler_id, gl.GL_TEXTURE_WRAP_T, 10497)
        gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0,
                        gl.GL_RGBA,
                        image.width, image.height, 0,
                        gl.GL_LUMINANCE,
                        gl.GL_UNSIGNED_BYTE,
                        np.array(list(image.getdata()), dtype=np.ubyte))
        gl.glGenerateMipmap(gl.GL_TEXTURE_2D)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
        if gl.glGetError() != gl.GL_NO_ERROR:
            raise Exception('failed to create font texture')
        buffer_id = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, buffer_id)
        buffer_data = np.array([0, 0, 0,
                                1, 0, 0,
                                1, 1, 0,
                                0, 1, 0]).tobytes()
        gl.glBufferData(gl.GL_ARRAY_BUFFER, len(buffer_data), buffer_data, gl.GL_STATIC_DRAW)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
        if gl.glGetError() != gl.GL_NO_ERROR:
            raise Exception('failed to create buffer')
        self._program_id = program_id
        self._attribute_locations = {attribute: gl.glGetAttribLocation(program_id, attribute)
                                     for attribute in ['a_position', 'a_texcoord0']}
        self._uniform_locations = {uniform: gl.glGetUniformLocation(program_id, uniform)
                                   for uniform in ['u_modelviewMatrix', 'u_projectionMatrix', 'u_fonttex', 'u_color']}
        self._texture_id = texture_id
        self._sampler_id = sampler_id
        self._buffer_id = buffer_id

    def draw_text(self, text, position=(0,0), scale=1, color=(1.0, 1.0, 1.0, 1.0)):
        gl.glUseProgram(self._program_id)
        gl.glActiveTexture(gl.GL_TEXTURE0+0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self._texture_id)
        gl.glBindSampler(gl.GL_SAMPLER_2D, self._sampler_id)
        gl.glUniform1i(self._uniform_locations['u_fonttex'], 0)
