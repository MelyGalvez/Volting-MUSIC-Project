import OpenGL
OpenGL.ERROR_CHECKING = False
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

from axis import draw_axis
from calibration import calibrate
from network import AsyncESP32Client
from skeleton import Skeleton
from recorder import Recorder
from config import STALE_AFTER


# ================================================
# MAIN
# ================================================


# ---------------- Configuration ------------------


WINDOW_SIZE = (900, 700)

AUTO_START_RECORDING = False

CAMERA_DISTANCE = 3.0
CAMERA_ROT_X = 20.0
CAMERA_ROT_Y = -30.0

ORBIT_SPEED = 0.5
ZOOM_SPEED = 0.2
MIN_DISTANCE = 1.0
MAX_DISTANCE = 10.0


# ------------------ Main loop --------------------


def run_opengl():
    """
    Run the complete Motion Capture application.

    This function initializes the OpenGL window, starts the
    asynchronous ESP32 acquisition thread, manages the user
    interface events, updates the camera, acquires IMU data,
    updates the skeleton, records the data when requested and
    renders the complete scene until the application exits.

    """

    pygame.init()

    pygame.display.set_mode(WINDOW_SIZE, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("ESP32 Motion Capture 3D")

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, WINDOW_SIZE[0] / WINDOW_SIZE[1], 0.1, 50)
    glMatrixMode(GL_MODELVIEW)

    glEnable(GL_DEPTH_TEST)
    glClearColor(0.1, 0.1, 0.12, 1.0)

    skeleton = Skeleton()
    recorder = Recorder()

    client = AsyncESP32Client()
    client.start()

    if AUTO_START_RECORDING:
        recorder.start()

    camera_distance = CAMERA_DISTANCE
    camera_rot_x = CAMERA_ROT_X
    camera_rot_y = CAMERA_ROT_Y

    mouse_down = False
    last_mouse_x = 0
    last_mouse_y = 0

    _print_controls()

    clock = pygame.time.Clock()
    running = True

    while running:

        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_down = True
                    last_mouse_x, last_mouse_y = pygame.mouse.get_pos()

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    mouse_down = False

            elif event.type == pygame.MOUSEMOTION:
                if mouse_down:
                    x, y = pygame.mouse.get_pos()
                    camera_rot_y += (x - last_mouse_x) * ORBIT_SPEED
                    camera_rot_x += (y - last_mouse_y) * ORBIT_SPEED
                    last_mouse_x = x
                    last_mouse_y = y

            elif event.type == pygame.MOUSEWHEEL:
                camera_distance -= event.y * ZOOM_SPEED
                camera_distance = max(MIN_DISTANCE,
                                      min(MAX_DISTANCE, camera_distance))

            elif event.type == pygame.KEYDOWN:

                if event.key == pygame.K_c:
                    print("Calibration...")
                    latest, _, _ = client.get()
                    if latest and calibrate(latest):
                        skeleton.resync()

                elif event.key == pygame.K_r:
                    if recorder.recording:
                        recorder.stop()
                    else:
                        recorder.start()

                elif event.key == pygame.K_ESCAPE:
                    running = False

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glTranslatef(0, 0, -camera_distance)
        glRotatef(camera_rot_x, 1, 0, 0)
        glRotatef(camera_rot_y, 0, 1, 0)
        glTranslatef(0, -0.5, 0)

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)


        data, _, age = client.get()


        if client.take_reboot():
            print("ESP32 reboot detected -> resync "
                  "(press C to recalibrate if the pose is offset)")
            skeleton.resync()


        fresh = data is not None and age < STALE_AFTER

        recorder.add(data if fresh else None)
        skeleton.update_from_imu(data if fresh else None)
        skeleton.advance(dt)

        draw_axis()
        skeleton.draw()

        pygame.display.flip()

    client.stop()
    recorder.stop()
    pygame.quit()


# ---------------- Controls help ------------------


def _print_controls():
    """
    Display the keyboard and mouse controls.

    Prints a short summary of every available interaction in the
    terminal when the application starts.

    """
    
    print()
    print("=================================================")
    print(" ESP32 Motion Capture 3D")
    print("-------------------------------------------------")
    print("  Mouse (drag) : orbit")
    print("  Scroll wheel : zoom")
    print("  R            : CSV recording on/off’")
    print("  C            : software recalibration (T-pose)")
    print("  ESC          : exit")
    print("=================================================")
    print()


# ------------- Program entry point ---------------


if __name__ == "__main__":
    run_opengl()