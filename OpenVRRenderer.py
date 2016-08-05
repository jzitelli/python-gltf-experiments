import numpy as np

import OpenGL.GL as gl

import openvr
from openvr.gl_renderer import OpenVrFramebuffer as OpenVRFramebuffer
from openvr.gl_renderer import matrixForOpenVrMatrix as matrixForOpenVRMatrix
from openvr.tracked_devices_actor import TrackedDevicesActor

from OpenGLRenderer import OpenGLRenderer


class OpenVRRenderer(OpenGLRenderer):
    def __init__(self, window_size=(800, 600), multisample=0):
        OpenGLRenderer.__init__(self, window_size=window_size)
        self.vr_system = openvr.init(openvr.VRApplication_Scene)
        w, h = self.vr_system.getRecommendedRenderTargetSize()
        self.vr_framebuffers = (OpenVRFramebuffer(w, h, multisample=multisample),
                                OpenVRFramebuffer(w, h, multisample=multisample))
        self.vr_compositor = openvr.VRCompositor()
        if self.vr_compositor is None:
            raise Exception('unable to create compositor')
        self.vr_framebuffers[0].init_gl()
        self.vr_framebuffers[1].init_gl()
        poses_t = openvr.TrackedDevicePose_t * openvr.k_unMaxTrackedDeviceCount
        self.poses = poses_t()
        zNear, zFar = 0.1, 1000
        self.projection_matrices = (np.asarray(matrixForOpenVRMatrix(self.vr_system.getProjectionMatrix(openvr.Eye_Left,
                                                                                                        zNear, zFar, openvr.API_OpenGL))),
                                    np.asarray(matrixForOpenVRMatrix(self.vr_system.getProjectionMatrix(openvr.Eye_Right,
                                                                                                        zNear, zFar, openvr.API_OpenGL))))
        self.view_matrices = (matrixForOpenVRMatrix(self.vr_system.getEyeToHeadTransform(openvr.Eye_Left)).I,
                              matrixForOpenVRMatrix(self.vr_system.getEyeToHeadTransform(openvr.Eye_Right)).I)
        self.controllers = TrackedDevicesActor(self.poses)
        self.controllers.show_controllers_only = False
        self.controllers.init_gl()
    def render(self):
        self.vr_compositor.waitGetPoses(self.poses, openvr.k_unMaxTrackedDeviceCount, None, 0)
        hmd_pose0 = self.poses[openvr.k_unTrackedDeviceIndex_Hmd]
        if not hmd_pose0.bPoseIsValid:
            return
        hmd_pose1 = hmd_pose0.mDeviceToAbsoluteTracking
        hmd_pose = matrixForOpenVRMatrix(hmd_pose1).I
        modelview = hmd_pose
        mvl = modelview * self.view_matrices[0]
        mvr = modelview * self.view_matrices[1]
        mvl = np.asarray(np.matrix(mvl, dtype=np.float32))
        mvr = np.asarray(np.matrix(mvr, dtype=np.float32))
        gl.glViewport(0, 0, self.vr_framebuffers[0].width, self.vr_framebuffers[0].height)
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.vr_framebuffers[0].fb)
        gl.glClearColor(0.5, 0.5, 0.5, 0.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        # draw...
        self.controllers.display_gl(mvl, self.projection_matrices[0])
        self.vr_framebuffers[0].submit(openvr.Eye_Left)
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.vr_framebuffers[1].fb)
        gl.glClearColor(0.5, 0.5, 0.5, 0.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        # draw...
        self.controllers.display_gl(mvr, self.projection_matrices[1])
        self.vr_framebuffers[1].submit(openvr.Eye_Right)
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)


if __name__ == "__main__":
    renderer = OpenVRRenderer()
    renderer.start_render_loop()
