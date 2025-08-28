import time
import math
import numpy as np
from PIL import Image, ImageDraw
import st7789

SPI_SPEED_MHZ = 80

# Display dimensions (adjust if your screen differs)
WIDTH, HEIGHT = 240, 240

# Initialize display
disp = st7789.ST7789(
    rotation=90,  # Needed to display the right way up on Pirate Audio
    port=0,       # SPI port
    cs=1,         # SPI port Chip-select channel
    dc=9,         # BCM pin used for data/command
    backlight=13,
    spi_speed_hz=SPI_SPEED_MHZ * 1000 * 1000
)

#disp.init()

# Define cube vertices in 3D
vertices = np.array([
    [-1, -1, -1],
    [-1, -1,  1],
    [-1,  1, -1],
    [-1,  1,  1],
    [ 1, -1, -1],
    [ 1, -1,  1],
    [ 1,  1, -1],
    [ 1,  1,  1]
])

# Define cube edges as pairs of vertex indices
edges = [
    (0, 1), (0, 2), (0, 4),
    (1, 3), (1, 5),
    (2, 3), (2, 6),
    (3, 7),
    (4, 5), (4, 6),
    (5, 7),
    (6, 7)
]

def project(point, angle_x, angle_y, angle_z, scale=80):
    """Rotate point in 3D and project to 2D screen coordinates."""
    # Rotation matrices
    Rx = np.array([
        [1, 0, 0],
        [0, math.cos(angle_x), -math.sin(angle_x)],
        [0, math.sin(angle_x), math.cos(angle_x)]
    ])
    Ry = np.array([
        [math.cos(angle_y), 0, math.sin(angle_y)],
        [0, 1, 0],
        [-math.sin(angle_y), 0, math.cos(angle_y)]
    ])
    Rz = np.array([
        [math.cos(angle_z), -math.sin(angle_z), 0],
        [math.sin(angle_z), math.cos(angle_z), 0],
        [0, 0, 1]
    ])

    rotated = Rz @ (Ry @ (Rx @ point))

    # Perspective projection (simple)
    distance = 4
    z = 1 / (distance - rotated[2])
    x = rotated[0] * z * scale + WIDTH // 2
    y = rotated[1] * z * scale + HEIGHT // 2
    return (int(x), int(y))

# Rotation angles
angle_x = angle_y = angle_z = 0

while True:
    # Create a blank image
    image = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Project all vertices
    projected = [project(v, angle_x, angle_y, angle_z) for v in vertices]

    # Draw edges
    for e in edges:
        draw.line([projected[e[0]], projected[e[1]]], fill=(0, 255, 0), width=2)

    # Display image
    disp.display(image)

    # Update angles
    angle_x += 0.05
    angle_y += 0.03
    angle_z += 0.02

    time.sleep(0.05)
