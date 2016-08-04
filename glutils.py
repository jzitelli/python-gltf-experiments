import numpy as np


def calc_ortho_matrix(left=-10, right=10, bottom=-10, top=10, znear=0.1, zfar=1000):
    dx = right - left
    dy = top - bottom
    dz = zfar - znear
    rx = -(right + left) / (right - left)
    ry = -(top + bottom) / (top - bottom)
    rz = -(zfar + znear) / (zfar - znear)
    return np.array([[2.0/dx, 0,            0, rx],
                     [0,      2.0/dy,       0, ry],
                     [0,      0,      -2.0/dz, rz],
                     [0,      0,            0,  1]])


def calc_projection_matrix(yfov=np.pi/3, aspectRatio=1.5, znear=0.1, zfar=1000, **kwargs):
    f = 1 / np.tan(yfov / 2)
    return np.array([[f / aspectRatio, 0, 0, 0],
                     [0, f, 0, 0],
                     [0, 0, (znear + zfar) / (znear - zfar), 2 * znear * zfar / (znear - zfar)],
                     [0, 0, -1, 0]])
