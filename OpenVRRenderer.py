from ctypes import c_float, cast, POINTER

import numpy as np

import OpenGL.GL as gl

import openvr
from openvr.gl_renderer import OpenVrFramebuffer as OpenVRFramebuffer
from openvr.gl_renderer import matrixForOpenVrMatrix as matrixForOpenVRMatrix
from openvr.tracked_devices_actor import TrackedDevicesActor


import gltfutils as gltfu


c_float_p = POINTER(c_float)


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
                                                                                                        znear, zfar))),
                                    np.asarray(matrixForOpenVRMatrix(self.vr_system.getProjectionMatrix(openvr.Eye_Right,
                                                                                                        znear, zfar))))
        self.eye_transforms = (np.asarray(matrixForOpenVRMatrix(self.vr_system.getEyeToHeadTransform(openvr.Eye_Left)).I),
                               np.asarray(matrixForOpenVRMatrix(self.vr_system.getEyeToHeadTransform(openvr.Eye_Right)).I))
        self.view = np.eye(4, dtype=np.float32)
        self.view_matrices  = (np.empty((4,4), dtype=np.float32),
                               np.empty((4,4), dtype=np.float32))
        self.controllers = TrackedDevicesActor(self.poses)
        self.controllers.show_controllers_only = False
        self.controllers.init_gl()
        self.vr_event = openvr.VREvent_t()

    def render(self, gltf, nodes, window_size=(800, 600)):
        self.vr_compositor.waitGetPoses(self.poses, openvr.k_unMaxTrackedDeviceCount, None, 0)
        hmd_pose = self.poses[openvr.k_unTrackedDeviceIndex_Hmd]
        if not hmd_pose.bPoseIsValid:
            return
        hmd_34 = np.ctypeslib.as_array(cast(hmd_pose.mDeviceToAbsoluteTracking.m, c_float_p),
                                       shape=(3,4))
        self.view[:3,:] = hmd_34
        view = np.linalg.inv(self.view.T)
        view.dot(self.eye_transforms[0], out=self.view_matrices[0])
        view.dot(self.eye_transforms[1], out=self.view_matrices[1])
        gl.glViewport(0, 0, self.vr_framebuffers[0].width, self.vr_framebuffers[0].height)
        for eye in (0, 1):
            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.vr_framebuffers[eye].fb)
            gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
            gltfu.set_material_state.current_material = None
            gltfu.set_technique_state.current_technique = None
            for node in nodes:
                gltfu.draw_node(node, gltf,
                                projection_matrix=self.projection_matrices[eye],
                                view_matrix=self.view_matrices[eye])
            self.controllers.display_gl(self.view_matrices[eye], self.projection_matrices[eye])
        self.vr_compositor.submit(openvr.Eye_Left, self.vr_framebuffers[0].texture)
        self.vr_compositor.submit(openvr.Eye_Right, self.vr_framebuffers[1].texture)
        # mirror left eye framebuffer to screen:
        gl.glBlitNamedFramebuffer(self.vr_framebuffers[0].fb, 0,
                                  0, 0, self.vr_framebuffers[0].width, self.vr_framebuffers[0].height,
                                  0, 0, window_size[0], window_size[1],
                                  gl.GL_COLOR_BUFFER_BIT, gl.GL_NEAREST)
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)

    def process_input(self):
        pass
        # state = self.vr_system.getControllerState(1)
        # if state and state.rAxis[1].x > 0.05:
        #     self.vr_system.triggerHapticPulse(1, 0, int(3200 * state.rAxis[1].x))
        # state = self.vr_system.getControllerState(2)
        # if state and state.rAxis[1].x > 0.05:
        #     self.vr_system.triggerHapticPulse(2, 0, int(3200 * state.rAxis[1].x))
        # if self.vr_system.pollNextEvent(self.vr_event):
        #     if self.vr_event.eventType == openvr.VREvent_ButtonPress:
        #         pass #print('vr controller button pressed')
        #     elif self.vr_event.eventType == openvr.VREvent_ButtonUnpress:
        #         pass #print('vr controller button unpressed')

    def shutdown(self):
        self.controllers.dispose_gl()
        openvr.shutdown()
