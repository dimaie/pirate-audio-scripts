import vlc
import time
from gpiozero import Button
from PIL import Image, ImageDraw
import st7789
import json

# ---- Load config ----
with open("config.json", "r") as f:
    config = json.load(f)

VOLUME_MIN = config["volume"]["min"]
VOLUME_MAX = config["volume"]["max"]
VOLUME_STEP = config["volume"]["step"]
DEFAULT_VOLUME = config["volume"]["default"]

# Pirate Audio buttons
btn_a = Button(5)   # Volume down
btn_b = Button(6)   # Volume up

# ---- VLC Setup ----
instance = vlc.Instance("--aout=alsa", "--alsa-audio-device=hw:1,0")
player = instance.media_player_new()
current_volume = DEFAULT_VOLUME
current_url = config["stations"][0]["url"]

# ---- Display Setup ----
disp = st7789.ST7789(height=240, width=240, rotation=90,
                     port=0, cs=1, dc=9, spi_speed_hz=80_000_000)
img = Image.new("RGB", (240, 240), color=(0, 0, 0))
draw = ImageDraw.Draw(img)

# ---- Functions ----
def update_display():
    img.paste((0, 0, 0), (0, 0, 240, 240))
    bar_width = int((current_volume / VOLUME_MAX) * 240)
    draw.rectangle((0, 100, bar_width, 140), fill=(0, 255, 0))
    disp.display(img)

def play_stream(url):
    global current_url
    current_url = url
    media = instance.media_new(url)
    player.set_media(media)
    player.play()
    time.sleep(1)
    player.audio_set_volume(current_volume)
    update_display()

def volume_up():
    global current_volume
    current_volume = min(VOLUME_MAX, current_volume + VOLUME_STEP)
    player.audio_set_volume(current_volume)
    update_display()

def volume_down():
    global current_volume
    current_volume = max(VOLUME_MIN, current_volume - VOLUME_STEP)
    player.audio_set_volume(current_volume)
    update_display()

# ---- Button handlers ----
btn_a.when_pressed = volume_down
btn_b.when_pressed = volume_up

# ---- Initial playback ----
play_stream(current_url)
update_display()
