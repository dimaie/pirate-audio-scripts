import vlc
import time
from gpiozero import Button
from PIL import Image, ImageDraw
import st7789
from flask import Flask, request, jsonify
import threading

# ---- CONFIG ----
current_url = "http://stream.live.vc.bbcmedia.co.uk/bbc_world_service"
VOLUME_STEP = 10
VOLUME_MIN = 0
VOLUME_MAX = 200

# Pirate Audio button pins (BCM numbering)
btn_a = Button(5)   # Volume down
btn_b = Button(6)   # Volume up

# ---- VLC Setup ----
instance = vlc.Instance("--aout=alsa", "--alsa-audio-device=hw:1,0")
player = instance.media_player_new()
current_volume = 100

# ---- Display Setup ----
disp = st7789.ST7789(
    height=240,
    width=240,
    rotation=90,
    port=0,
    cs=1,
    dc=9,
    spi_speed_hz=80_000_000
)

# Pillow image buffer
img = Image.new("RGB", (240, 240), color=(0, 0, 0))
draw = ImageDraw.Draw(img)

def update_display():
    """Draw a horizontal green bar proportional to volume."""
    img.paste((0, 0, 0), (0, 0, 240, 240))  # clear screen
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

# Initial playback and draw
play_stream(current_url)
update_display()

# ---- Web Server ----
app = Flask(__name__)

@app.route("/")
def index():
    return f"""
    <html>
      <head><title>Pirate Audio Control</title></head>
      <body style="font-family:sans-serif; margin:2em;">
        <h2>Current Stream</h2>
        <p>{current_url}</p>
        <form action="/set_url" method="post">
          <input type="text" name="url" size="50" placeholder="Stream URL">
          <button type="submit">Set Stream</button>
        </form>
        <h2>Volume</h2>
        <p>Current: {current_volume}</p>
        <form action="/set_volume" method="post">
          <input type="number" name="volume" min="{VOLUME_MIN}" max="{VOLUME_MAX}" value="{current_volume}">
          <button type="submit">Set Volume</button>
        </form>
      </body>
    </html>
    """

@app.route("/set_url", methods=["POST"])
def set_url():
    url = request.form.get("url")
    if not url:
        return "Missing url", 400
    play_stream(url)
    return f"Stream set to {url}", 200

@app.route("/set_volume", methods=["POST"])
def set_volume():
    global current_volume
    try:
        vol = int(request.form.get("volume"))
    except (TypeError, ValueError):
        return "Invalid volume", 400
    current_volume = max(VOLUME_MIN, min(VOLUME_MAX, vol))
    player.audio_set_volume(current_volume)
    update_display()
    return f"Volume set to {current_volume}", 200

@app.route("/status")
def status():
    return jsonify({"url": current_url, "volume": current_volume})

def run_web():
    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=run_web, daemon=True).start()

# ---- Main Loop ----
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    player.stop()
