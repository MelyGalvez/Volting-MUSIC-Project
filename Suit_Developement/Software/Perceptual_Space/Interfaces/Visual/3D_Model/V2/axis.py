from OpenGL.GL import *
from OpenGL.GLU import *


# ================================================
# AXIS
# ================================================


def draw_axis(length=0.5):
    """
    Draw the global Cartesian coordinate system.

    Renders the three world axes used as a visual reference
    in the OpenGL scene.
    
    Axis colors:
        - X : Red
        - Y : Green
        - Z : Blue
    
    The axes originate from the world origin (0, 0, 0).
    
    """


    glLineWidth(3)


    glBegin(GL_LINES)


    glColor3f(
        1,
        0,
        0
    )

    glVertex3f(
        0,
        0,
        0
    )

    glVertex3f(
        length,
        0,
        0
    )


    glColor3f(
        0,
        1,
        0
    )

    glVertex3f(
        0,
        0,
        0
    )

    glVertex3f(
        0,
        length,
        0
    )


    glColor3f(
        0,
        0,
        1
    )

    glVertex3f(
        0,
        0,
        0
    )

    glVertex3f(
        0,
        0,
        length
    )


    glEnd()


    glColor3f(
        1,
        1,
        1
    )