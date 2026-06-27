"""
transformations.py — Matrix and vector math utilities.

All matrices are 4×4 NumPy arrays in column-major order (matching OpenGL).
We work in homogeneous coordinates so a 3-D point is represented as (x,y,z,1)
and a direction vector as (x,y,z,0).

Transformation pipeline reminder:
    clip = Projection × View × Model × local_point
                                 ^^^^^^
                   this module builds the Model and helpers
"""

import numpy as np
from typing import List, Tuple


# ---------------------------------------------------------------------------
# Basic constructors
# ---------------------------------------------------------------------------

def identity() -> np.ndarray:
    """Return a 4×4 identity matrix."""
    return np.eye(4, dtype=np.float64)


def translation(tx: float, ty: float, tz: float) -> np.ndarray:
    """
    Build a translation matrix.

    Moving a point from model-space to world-space by (tx, ty, tz):
        P_world = T × P_model
    """
    m = identity()
    m[0, 3] = tx
    m[1, 3] = ty
    m[2, 3] = tz
    return m


def scaling(sx: float, sy: float, sz: float) -> np.ndarray:
    """
    Build a uniform or non-uniform scaling matrix.

    Scale factors < 1 shrink, > 1 enlarge the object.
    Negative values mirror (reflect) along that axis.
    """
    m = identity()
    m[0, 0] = sx
    m[1, 1] = sy
    m[2, 2] = sz
    return m


def rotation_x(angle_deg: float) -> np.ndarray:
    """Rotation around the X axis by *angle_deg* degrees."""
    a = np.radians(angle_deg)
    c, s = np.cos(a), np.sin(a)
    m = identity()
    m[1, 1] =  c;  m[1, 2] = -s
    m[2, 1] =  s;  m[2, 2] =  c
    return m


def rotation_y(angle_deg: float) -> np.ndarray:
    """Rotation around the Y axis by *angle_deg* degrees."""
    a = np.radians(angle_deg)
    c, s = np.cos(a), np.sin(a)
    m = identity()
    m[0, 0] =  c;  m[0, 2] =  s
    m[2, 0] = -s;  m[2, 2] =  c
    return m


def rotation_z(angle_deg: float) -> np.ndarray:
    """Rotation around the Z axis by *angle_deg* degrees."""
    a = np.radians(angle_deg)
    c, s = np.cos(a), np.sin(a)
    m = identity()
    m[0, 0] =  c;  m[0, 1] = -s
    m[1, 0] =  s;  m[1, 1] =  c
    return m


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize(v: np.ndarray) -> np.ndarray:
    """Return a unit vector; safe-guard against zero-length input."""
    n = np.linalg.norm(v)
    if n < 1e-10:
        return v
    return v / n


def apply_matrix(m: np.ndarray, point: np.ndarray) -> np.ndarray:
    """
    Multiply a 4×4 matrix by a 3-D point (promoted to homogeneous coords).
    Returns a 3-D point (perspective divide applied).
    """
    h = np.array([point[0], point[1], point[2], 1.0])
    r = m @ h
    if abs(r[3]) > 1e-10:
        r /= r[3]
    return r[:3]


def apply_matrix_dir(m: np.ndarray, direction: np.ndarray) -> np.ndarray:
    """
    Multiply a 4×4 matrix by a 3-D *direction* vector (w=0 so translation
    is ignored — only the linear part of the transform is applied).
    """
    h = np.array([direction[0], direction[1], direction[2], 0.0])
    return (m @ h)[:3]


# ---------------------------------------------------------------------------
# Ray utilities
# ---------------------------------------------------------------------------

def ray_aabb_intersect(
    ray_origin: np.ndarray,
    ray_dir: np.ndarray,
    aabb_min: np.ndarray,
    aabb_max: np.ndarray,
) -> Tuple[bool, float]:
    """
    Slab-based ray vs. Axis-Aligned Bounding Box test.

    The "slab" method checks each pair of parallel planes that bound the box.
    A ray hits the box only when all three pairs of slabs overlap.

    Returns (hit: bool, t: float) where t is the distance to the near hit.
    t < 0 means the box is behind the ray origin (no forward hit).
    """
    tmin = -np.inf
    tmax =  np.inf

    for i in range(3):
        if abs(ray_dir[i]) < 1e-8:
            # Ray is parallel to this slab — only inside if origin is in range
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
