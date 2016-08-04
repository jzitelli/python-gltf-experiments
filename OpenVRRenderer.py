import openvr

from OpenGLRenderer import OpenGLRenderer


class OpenVRRenderer(OpenGLRenderer):
    def __init__(self, window_size=(800, 600)):
        OpenGLRenderer.__init__(self, window_size=window_size)
        self.vr_system = openvr.init(openvr.VRApplication_Scene)
