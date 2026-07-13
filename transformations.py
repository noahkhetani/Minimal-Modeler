"""
matrix and vector math.

matrices are 4x4 numpy arrays, column-major to match opengl. everything's in
homogeneous coords so a point is (x,y,z,1) and a direction is (x,y,z,0).

pipeline: clip = projection x view x model x local_point. this file builds the
model part plus some helpers.
"""

import numpy as np
from typing import List, Tuple


def identity() -> np.ndarray:
    return np.eye(4, dtype=np.float64)


def translation(tx: float, ty: float, tz: float) -> np.ndarray:
    # moves a point from model space to world space by (tx, ty, tz)
    m = identity()
    m[0, 3] = tx
    m[1, 3] = ty
    m[2, 3] = tz
    return m


def scaling(sx: float, sy: float, sz: float) -> np.ndarray:
    # <1 shrinks, >1 grows, negative mirrors along that axis
    m = identity()
    m[0, 0] = sx
    m[1, 1] = sy
    m[2, 2] = sz
    return m


def rotation_x(angle_deg: float) -> np.ndarray:
    a = np.radians(angle_deg)
    c, s = np.cos(a), np.sin(a)
    m = identity()
    m[1, 1] =  c;  m[1, 2] = -s
    m[2, 1] =  s;  m[2, 2] =  c
    return m


def rotation_y(angle_deg: float) -> np.ndarray:
    a = np.radians(angle_deg)
    c, s = np.cos(a), np.sin(a)
    m = identity()
    m[0, 0] =  c;  m[0, 2] =  s
    m[2, 0] = -s;  m[2, 2] =  c
    return m


def rotation_z(angle_deg: float) -> np.ndarray:
    a = np.radians(angle_deg)
    c, s = np.cos(a), np.sin(a)
    m = identity()
    m[0, 0] =  c;  m[0, 1] = -s
    m[1, 0] =  s;  m[1, 1] =  c
    return m


def normalize(v: np.ndarray) -> np.ndarray:
    # unit vector, but don't divide by zero
    n = np.linalg.norm(v)
    if n < 1e-10:
        return v
    return v / n


def apply_matrix(m: np.ndarray, point: np.ndarray) -> np.ndarray:
    # 4x4 times a 3d point (bumped to homogeneous), with the perspective divide
    h = np.array([point[0], point[1], point[2], 1.0])
    r = m @ h
    if abs(r[3]) > 1e-10:
        r /= r[3]
    return r[:3]


def apply_matrix_dir(m: np.ndarray, direction: np.ndarray) -> np.ndarray:
    # same but for a direction (w=0 so translation is ignored)
    h = np.array([direction[0], direction[1], direction[2], 0.0])
    return (m @ h)[:3]


def ray_aabb_intersect(
    ray_origin: np.ndarray,
    ray_dir: np.ndarray,
    aabb_min: np.ndarray,
    aabb_max: np.ndarray,
) -> Tuple[bool, float]:
    """
    slab-based ray vs axis-aligned box test.

    the slab method checks each pair of parallel planes around the box - the
    ray only hits if all three slab ranges overlap. returns (hit, t) where t is
    the near hit distance; t < 0 means the box is behind us.
    """
    tmin = -np.inf
    tmax =  np.inf

    for i in range(3):
        if abs(ray_dir[i]) < 1e-8:
            # ray runs parallel to this slab - only ok if the origin's inside it
            if ray_origin[i] < aabb_min[i] or ray_origin[i] > aabb_max[i]:
                return False, np.inf
        else:
            t1 = (aabb_min[i] - ray_origin[i]) / ray_dir[i]
            t2 = (aabb_max[i] - ray_origin[i]) / ray_dir[i]
            tmin = max(tmin, min(t1, t2))
            tmax = min(tmax, max(t1, t2))

    if tmax >= tmin and tmax >= 0:
        return True, max(tmin, 0.0)
    return False, np.inf
