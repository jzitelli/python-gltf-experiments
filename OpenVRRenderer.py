import numpy as np

import OpenGL.GL as gl

import cyglfw3 as glfw

import openvr
from openvr.gl_renderer import OpenVrFramebuffer as OpenVRFramebuffer
from openvr.gl_renderer import matrixForOpenVrMatrix as matrixForOpenVRMatrix
from openvr.tracked_devices_actor import TrackedDevicesActor


import gltfutils as gltfu
from OpenGLRenderer import OpenGLRenderer


class OpenVRRenderer(OpenGLRenderer):
    def __init__(self, window_size=(800, 600), multisample=0, znear=0.1, zfar=1000):
        OpenGLRenderer.__init__(self, window_size=window_size, double_buffered=False)
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
        self.view_matrices = (matrixForOpenVRMatrix(self.vr_system.getEyeToHeadTransform(openvr.Eye_Left)).I,
                              matrixForOpenVRMatrix(self.vr_system.getEyeToHeadTransform(openvr.Eye_Right)).I)
        self.modelview_left  = np.eye(4, dtype=np.float32)
        self.modelview_right = np.eye(4, dtype=np.float32)
        self.controllers = TrackedDevicesActor(self.poses)
        self.controllers.show_controllers_only = False
        self.controllers.init_gl()
        self.scene = None
        gl.glViewport(0, 0, self.vr_framebuffers[0].width, self.vr_framebuffers[0].height)
    def set_scene(self, gltf, uri_path, scene_name=None):
        if scene_name is None:
            scene_name = gltf.scene
        gltfu.setup_shaders(gltf, uri_path)
        gltfu.setup_programs(gltf)
        gltfu.setup_textures(gltf, uri_path)
        gltfu.setup_buffers(gltf, uri_path)
        self.gltf = gltf
        self.scene = gltf.scenes[scene_name]
        self.nodes = [self.gltf.nodes[n] for n in self.scene.nodes]
        for node in self.nodes:
            gltfu.update_world_matrices(node, gltf)
    def render(self):
        self.vr_compositor.waitGetPoses(self.poses, openvr.k_unMaxTrackedDeviceCount, None, 0)
        hmd_pose = self.poses[openvr.k_unTrackedDeviceIndex_Hmd]
        if not hmd_pose.bPoseIsValid:
            return
        modelview = matrixForOpenVRMatrix(hmd_pose.mDeviceToAbsoluteTracking).I
        self.modelview_left[...]  = modelview * self.view_matrices[0]
        self.modelview_right[...] = modelview * self.view_matrices[1]
            
        # draw left eye...
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.vr_framebuffers[0].fb)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        for node in self.nodes:
            gltfu.draw_node(node, self.gltf,
                            projection_matrix=self.projection_matrices[0].T,
                            view_matrix=self.modelview_left.T)
        self.controllers.display_gl(self.modelview_left, self.projection_matrices[0])
        self.vr_compositor.submit(openvr.Eye_Left, self.vr_framebuffers[0].texture)
        #self.vr_framebuffers[0].submit(openvr.Eye_Left)

        # draw right eye...
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.vr_framebuffers[1].fb)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        for node in self.nodes:
            gltfu.draw_node(node, self.gltf,
                            projection_matrix=self.projection_matrices[1].T,
                            view_matrix=self.modelview_right.T)
        self.controllers.display_gl(self.modelview_right, self.projection_matrices[1])
        self.vr_compositor.submit(openvr.Eye_Right, self.vr_framebuffers[1].texture)
        #self.vr_framebuffers[1].submit(openvr.Eye_Right)
                            
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)
    def start_render_loop(self):
        while not glfw.WindowShouldClose(self.window):
            glfw.PollEvents()
            self.render()
            glfw.SwapBuffers(self.window)
        print('* closing window...')
        self.controllers.dispose_gl()
        openvr.shutdown()
        glfw.DestroyWindow(self.window)
        glfw.Terminate()
