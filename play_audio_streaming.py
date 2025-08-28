import vlc
import time
from gpiozero import Button
from PIL import Image, ImageDraw
import st7789

# ---- CONFIG ----
url = "http://stream.live.vc.bbcmedia.co.uk/bbc_world_service"
VOLUME_STEP = 10       # step size for each button press
VOLUME_MIN = 0
VOLUME_MAX = 100

# Pirate Audio button pins (BCM numbering)
btn_a = Button(5)   # Volume down
btn_b = Button(6)   # Volume up

# ---- VLC Setup ----
instance = vlc.Instance("--aout=alsa", "--alsa-audio-device=hw:1,0")
player = instance.media_player_new()
media = instance.media_new(url)
player.set_media(media)

player.play()
time.sleep(1)

current_volume = 50
player.audio_set_volume(current_volume)
# ---- Display Setup ----
disp = st7789.ST7789(
    rotation=90,
    port=0,
    cs=1,
    dc=9,
    backlight=13,
    spi_speed_hz=80_000_000
)

# Pillow image buffer
img = Image.new("RGB", (240, 240), color=(0, 0, 0))
draw = ImageDraw.Draw(img)

def update_display():
    """Draw a horizontal green bar proportional to volume."""
    img.paste((0, 0, 0), (0, 0, 240, 240))  # clear screen

    # compute bar width (max 240 pixels)
    bar_width = int((current_volume / VOLUME_MAX) * 240)
    draw.rectangle((0, 100, bar_width, 140), fill=(0, 255, 0))  # green bar

    # push image to display
    disp.display(img)

# ---- Button Handlers ----
def volume_up():
    global current_volume
    current_volume = min(VOLUME_MAX, current_volume + VOLUME_STEP)
    player.audio_set_volume(current_volume)
    print(f"Volume up: {current_volume}")
    update_display()

def volume_down():
    global current_volume
    current_volume = max(VOLUME_MIN, current_volume - VOLUME_STEP)
    player.audio_set_volume(current_volume)
    print(f"Volume down: {current_volume}")
    update_display()

btn_a.when_pressed = volume_down
btn_b.when_pressed = volume_up

# Initial draw
update_display()

# ---- Main Loop ----
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    player.stop()
