import vlc
import time
from gpiozero import Button, LED
from PIL import Image, ImageDraw, ImageFont
import st7789
import json
import threading

# ---- Backlight ----
BACKLIGHT_PIN = 13
backlight = LED(BACKLIGHT_PIN)
backlight.on()  # turn on at startup

# ---- Load config ----
with open("config.json", "r") as f:
    config = json.load(f)

stations = config["stations"]
VOLUME_MIN = config["volume"]["min"]
VOLUME_MAX = config["volume"]["max"]
VOLUME_STEP = config["volume"]["step"]
DEFAULT_VOLUME = config["volume"]["default"]
DISPLAY_TIMEOUT = 30  # seconds

_last_activity = time.time()
_display_on = True

def reset_idle_timer():
    global _last_activity, _display_on
    _last_activity = time.time()
    if not _display_on:
        _display_on = True
        update_display()

# Map url -> label
url_to_label = {s["url"]: s["label"] for s in stations}

# ---- Buttons ----
button_timer = Button(24)
btn_a = Button(5)  # volume down
btn_b = Button(6)  # volume up
btn_c = Button(16) # mute toggle

# ---- VLC ----
instance = vlc.Instance("--aout=alsa", "--alsa-audio-device=hw:1,0")
player = instance.media_player_new()
current_volume = DEFAULT_VOLUME

# ---- Current stream ----
current_url = stations[0]["url"]
current_label = stations[0]["label"]

# ---- Display Setup ----
disp = st7789.ST7789(height=240, width=240, rotation=90, port=0, cs=1, dc=9, spi_speed_hz=80_000_000)
img = Image.new("RGB", (240, 240), color=(0, 0, 0))
draw = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
except:
    font = None

# ---- Timer state ----
timer_enabled = False
timer_end = None
timer_interval = config["timer"]["interval"]  # minutes
_timer_lock = threading.Lock()

# ---- Display ----
def update_display():
    global _last_activity, _display_on
    _last_activity = time.time()
    if not _display_on:
        backlight.on()
        _display_on = True

    img.paste((0, 0, 0), (0, 0, 240, 240))

    # station label
    text_width, _ = draw.textsize(current_label, font=font)
    draw.text(((240 - text_width)//2, 20), current_label, fill=(0, 255, 0), font=font)

    # mute
    if is_muted:
        mute_text = "MUTED"
        text_width, _ = draw.textsize(mute_text, font=font)
        draw.text(((240 - text_width)//2, 50), mute_text, fill=(0, 255, 0), font=font)

    # volume bar
    bar_max_width = 180
    bar_width = int((current_volume / VOLUME_MAX) * bar_max_width)
    draw.rectangle(((30, 40), (30 + bar_width, 45)), fill=(0, 255, 0))

    # timer
    timer_text = f"Timer: {get_timer_status()}"
    w, _ = draw.textsize(timer_text, font=font)
    draw.text(((240 - w)//2, 70), timer_text, fill=(0, 255, 0), font=font)

    # stopped by timer
    with _timer_lock:
        if timer_enabled and timer_end and time.time() >= timer_end:
            stop_text = "STOPPED BY TIMER"
            w, _ = draw.textsize(stop_text, font=font)
            draw.text(((240 - w)//2, 90), stop_text, fill=(255, 0, 0), font=font)

    disp.display(img)

# ---- Stream ----
def play_stream(url):
    global current_url, current_label
    current_url = url
    current_label = url_to_label.get(url, "Unknown Station")

    media = instance.media_new(url, "network-caching=1500")
    player.set_media(media)
    player.play()
    time.sleep(1)
    player.audio_set_volume(current_volume)
    update_display()

# ---- Mute ----
is_muted = False
def toggle_mute():
    global is_muted
    player.audio_toggle_mute()
    is_muted = not is_muted
    update_display()
    print(f"Muted: {is_muted}")

# ---- Volume ----
def volume_up():
    global current_volume
    current_volume = min(VOLUME_MAX, current_volume + VOLUME_STEP)
    player.audio_set_volume(current_volume)
    update_display()
    print(f"Volume up: {current_volume}")

def volume_down():
    global current_volume
    current_volume = max(VOLUME_MIN, current_volume - VOLUME_STEP)
    player.audio_set_volume(current_volume)
    update_display()
    print(f"Volume down: {current_volume}")

# ---- Timer ----
def get_timer_status():
    with _timer_lock:
        if timer_enabled and timer_end is not None:
            remaining = max(0, int((timer_end - time.time()) / 60))
            return f"ON ({remaining} min left)"
    return "OFF"

def _monitor_timer():
    """Background thread that stops the player when timer expires."""
    global timer_enabled, timer_end
    while True:
        with _timer_lock:
            if timer_enabled and timer_end is not None and time.time() >= timer_end:
                try:
                    player.stop()
                    print("Player stopped")
                except Exception as e:
                    print(f"Error stopping VLC: {e}")
                stop_timer()
                update_display()
        time.sleep(1)

threading.Thread(target=_monitor_timer, daemon=True).start()

def start_timer():
    global timer_enabled, timer_end
    with _timer_lock:
        timer_enabled = True
        timer_end = time.time() + (timer_interval * 60)
    update_display()

def stop_timer():
    global timer_enabled, timer_end
    with _timer_lock:
        timer_enabled = False
        timer_end = None
    update_display()

def toggle_timer():
    if timer_enabled:
        stop_timer()
    else:
        start_timer()

def set_timer_interval(minutes):
    global timer_interval
    timer_interval = minutes
    if timer_enabled:
        start_timer()  # restart with new interval

button_timer.when_pressed = toggle_timer

# ---- Idle display monitor ----
def idle_display_monitor():
    global _display_on
    while True:
        if _display_on and time.time() - _last_activity > DISPLAY_TIMEOUT:
            backlight.off()
            _display_on = False
        time.sleep(1)

threading.Thread(target=idle_display_monitor, daemon=True).start()

# ---- Button events ----
btn_a.when_pressed = volume_down
btn_b.when_pressed = volume_up
btn_c.when_pressed = toggle_mute

# ---- Initial playback ----
play_stream(current_url)
update_display()
