# ================================================
# MATHUTILS
# ================================================


def add(a, b):
    """
    Add two 3D vectors.
    
    """
    
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def scale(v, s):
    """
    Scale a 3D vector by a scalar.
    
    """
    
    return (v[0] * s, v[1] * s, v[2] * s)