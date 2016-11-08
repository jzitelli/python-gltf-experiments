import numpy as np

import OpenGL.GL as gl

import openvr
from openvr.gl_renderer import OpenVrFramebuffer as OpenVRFramebuffer
from openvr.gl_renderer import matrixForOpenVrMatrix as matrixForOpenVRMatrix
from openvr.tracked_devices_actor import TrackedDevicesActor


import gltfutils as gltfu


class OpenVRRenderer(object):
    def __init__(self, multisample=0, znear=0.1, zfar=1000):
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
        self.projection_matrices = (np.asarray(matrixForOpenVRMatrix(self.vr_system.getProjectionMatrix(openvr.Eye_Left,
                                                                                                        znear, zfar, openvr.API_OpenGL))),
                                    np.asarray(matrixForOpenVRMatrix(self.vr_system.getProjectionMatrix(openvr.Eye_Right,
                                                                                                        znear, zfar, openvr.API_OpenGL))))
        self.eye_transforms = (np.asarray(matrixForOpenVRMatrix(self.vr_system.getEyeToHeadTransform(openvr.Eye_Left)).I),
                               np.asarray(matrixForOpenVRMatrix(self.vr_system.getEyeToHeadTransform(openvr.Eye_Right)).I))
        self.view_left  = np.empty((4,4), dtype=np.float32)
        self.view_right = np.empty((4,4), dtype=np.float32)
        self.controllers = TrackedDevicesActor(self.poses)
        self.controllers.show_controllers_only = False
        self.controllers.init_gl()
    def render(self, gltf, nodes, window_size=(800, 600)):
        self.vr_compositor.waitGetPoses(self.poses, openvr.k_unMaxTrackedDeviceCount, None, 0)
        hmd_pose = self.poses[openvr.k_unTrackedDeviceIndex_Hmd]
        if not hmd_pose.bPoseIsValid:
            return
        view = np.asarray(matrixForOpenVRMatrix(hmd_pose.mDeviceToAbsoluteTracking).I)
        view.dot(self.eye_transforms[0], out=self.view_left)
        view.dot(self.eye_transforms[1], out=self.view_right)

        # draw left eye:
        gl.glViewport(0, 0, self.vr_framebuffers[0].width, self.vr_framebuffers[0].height)
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.vr_framebuffers[0].fb)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        for node in nodes:
            gltfu.draw_node(node, gltf,
                            projection_matrix=self.projection_matrices[0],
                            view_matrix=self.view_left)
        self.controllers.display_gl(self.view_left, self.projection_matrices[0])

        # mirror left eye framebuffer to screen:
        gl.glBlitNamedFramebuffer(self.vr_framebuffers[0].fb, 0,
                                  0, 0, self.vr_framebuffers[0].width, self.vr_framebuffers[0].height,
                                  0, 0, window_size[0], window_size[1],
                                  gl.GL_COLOR_BUFFER_BIT, gl.GL_NEAREST)

        # draw right eye:
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.vr_framebuffers[1].fb)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        for node in nodes:
            gltfu.draw_node(node, gltf,
                            projection_matrix=self.projection_matrices[1],
                            view_matrix=self.view_right)
        self.controllers.display_gl(self.view_right, self.projection_matrices[1])

        self.vr_compositor.submit(openvr.Eye_Left, self.vr_framebuffers[0].texture)
        self.vr_compositor.submit(openvr.Eye_Right, self.vr_framebuffers[1].texture)



        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)

    def shutdown(self):
        self.controllers.dispose_gl()
        openvr.shutdown()
