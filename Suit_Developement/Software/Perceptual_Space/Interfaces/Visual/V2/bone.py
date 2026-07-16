from OpenGL.GL import *
from OpenGL.GLU import *

from quaternion import identity, rotate_vector
from mathutils import add, scale


# ================================================
# BONE
# ================================================


_quadric = None


def _joint_quadric():
    """
    Return the shared OpenGL quadric object.

    Creates the quadric object the first time it is requested,
    then reuses the same instance for every joint to avoid
    unnecessary allocations.

    """
    
    global _quadric
    if _quadric is None:
        _quadric = gluNewQuadric()
    return _quadric


# ---------------------- BONE ---------------------


class Bone:
    """
    Represents one rigid body segment of the skeleton.
    
    A Bone stores its length, its rest direction in the T-pose,
    and its current orientation represented as a quaternion.
    It provides forward kinematics and OpenGL rendering
    functions.
    
    """

    def __init__(self, length, direction=(0.0, 1.0, 0.0)):
        """
        Initialize a bone.
        
        Stores the bone length, its default direction in the
        reference T-pose and initializes its orientation with
        the identity quaternion.
        
        """
        
        self.length = length

        self.direction = direction

        self.quat = identity()


# ------------------- Kinematics ------------------


    def vector(self):
        """
        Compute the current bone vector.

        Rotates the rest direction using the current quaternion
        and scales it by the bone length.
    
        """
        
        return scale(rotate_vector(self.quat, self.direction), self.length)

    def end_position(self, start):
        """
        Compute the end position of the bone.
    
        Computes the endpoint of the segment from its start
        position and current orientation.
    
        """
        
        return add(start, self.vector())


# ------------------- Rendering -------------------


    def draw(self, start):
        """
        Render the bone.
    
        Draws the joint as a sphere and the bone as a line
        between the start and end positions.
    
        """
        end = self.end_position(start)

        glColor3f(0.2, 0.6, 1.0)
        glPushMatrix()
        glTranslatef(start[0], start[1], start[2])
        gluSphere(_joint_quadric(), 0.03, 12, 12)
        glPopMatrix()

        glLineWidth(4)
        glColor3f(0.95, 0.85, 0.2)
        glBegin(GL_LINES)
        glVertex3f(start[0], start[1], start[2])
        glVertex3f(end[0], end[1], end[2])
        glEnd()

        glColor3f(1.0, 1.0, 1.0)