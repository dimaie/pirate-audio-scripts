#!/usr/bin/env python3
import vlc
import time
import json
import threading
import phatbeat_gpiozero as phatbeat

# ---- Load config ----
with open("config.json", "r") as f:
    config = json.load(f)

stations = config["stations"]
VOLUME_MIN = config["volume"]["min"]
VOLUME_MAX = config["volume"]["max"]
VOLUME_STEP = config["volume"]["step"]
DEFAULT_VOLUME = config["volume"]["default"]

# ---- Button pin numbers (BCM) ----
BTN_REWIND = 13
BTN_FFWD = 5
BTN_PLAYPAUSE = 6
BTN_VOLUP = 16
BTN_VOLDN = 26
BTN_ONOFF = 12

# ---- VLC setup ----
instance = vlc.Instance("--aout=alsa", "--alsa-audio-device=hw:1,0")
player = instance.media_player_new()
current_volume = DEFAULT_VOLUME
player.audio_set_volume(current_volume)

# ---- Current station state ----
station_index = 0
current_url = stations[station_index]["url"]
current_label = stations[station_index]["label"]
is_muted = False

# ---- LED helpers ----
def led_flash(color, duration=0.18):
    phatbeat.set_all(*color, brightness=0.5)
    phatbeat.show()
    time.sleep(duration)
    phatbeat.clear()
    phatbeat.show()

def led_pulse(color, steps=8, hold=0.02):
    r, g, b = color
    for t in range(steps):
        bness = (t + 1) / steps
        phatbeat.set_all(int(r * bness), int(g * bness), int(b * bness), brightness=bness)
        phatbeat.show()
        time.sleep(hold)
    for t in range(steps - 1, -1, -1):
        bness = (t + 1) / steps
        phatbeat.set_all(int(r * bness), int(g * bness), int(b * bness), brightness=bness)
        phatbeat.show()
        time.sleep(hold)
    phatbeat.clear()
    phatbeat.show()

# ---- Playback control ----
def play_stream(url):
    global current_url, current_label
    current_url = url
    current_label = next((s["label"] for s in stations if s["url"] == url), "Unknown")
    media = instance.media_new(url, "network-caching=1500")
    player.set_media(media)
    player.play()
    time.sleep(1)
    player.audio_set_volume(current_volume)
    print(f"Playing: {current_label}")

def next_station():
    global station_index
    station_index = (station_index + 1) % len(stations)
    led_flash((255, 0, 0))
    play_stream(stations[station_index]["url"])

def prev_station():
    global station_index
    station_index = (station_index - 1) % len(stations)
    led_flash((255, 0, 255))
    play_stream(stations[station_index]["url"])

def toggle_mute():
    global is_muted
    player.audio_toggle_mute()
    is_muted = not is_muted
    led_pulse((255, 200, 0), steps=6, hold=0.03)
    print("Muted" if is_muted else "Unmuted")

def volume_up():
    global current_volume
    current_volume = min(VOLUME_MAX, current_volume + VOLUME_STEP)
    player.audio_set_volume(current_volume)
    led_flash((0, 255, 0))
    print("Volume up:", current_volume)

def volume_down():
    global current_volume
    current_volume = max(VOLUME_MIN, current_volume - VOLUME_STEP)
    player.audio_set_volume(current_volume)
    led_flash((0, 0, 255))
    print("Volume down:", current_volume)
# ---- Update display ----
def update_display():
    # No actual screen, just a placeholder
    pass
# ---- Timer status helper ----
def get_timer_status():
    with _timer_lock:
        if timer_enabled and timer_end is not None:
            remaining = max(0, int((timer_end - time.time()) / 60))
            return f"ON ({remaining} min left)"
    return "OFF"
# ---- Timer support ----
timer_enabled = False
timer_end = None
timer_interval = config["timer"]["interval"]
_timer_lock = threading.Lock()

def _monitor_timer():
    global timer_enabled, timer_end
    while True:
        expired = False
        with _timer_lock:
            if timer_enabled and timer_end is not None and time.time() >= timer_end:
                expired = True
                timer_enabled = False
                timer_end = None
        if expired:
            print("Timer expired — stopping playback")
            player.stop()
            led_flash((255, 0, 0))
        time.sleep(1)

threading.Thread(target=_monitor_timer, daemon=True).start()

def toggle_timer():
    global timer_enabled, timer_end
    with _timer_lock:
        if timer_enabled:
            timer_enabled = False
            timer_end = None
            led_flash((128, 0, 0))
            print("Timer stopped")
        else:
            timer_enabled = True
            timer_end = time.time() + (timer_interval * 60)
            led_flash((0, 128, 0))
            print(f"Timer started for {timer_interval} min")

# ---- Hook up buttons ----
@phatbeat.on(BTN_FFWD)
def handle_next(pin): next_station()

@phatbeat.on(BTN_REWIND)
def handle_prev(pin): prev_station()

@phatbeat.on(BTN_PLAYPAUSE)
def handle_play_pause(pin): toggle_mute()

@phatbeat.on(BTN_VOLUP)
def handle_vol_up(pin): volume_up()

@phatbeat.on(BTN_VOLDN)
def handle_vol_down(pin): volume_down()

@phatbeat.on(BTN_ONOFF)
def handle_timer(pin): toggle_timer()

# ---- Initial setup ----
phatbeat.clear()
phatbeat.show()
play_stream(current_url)

print("pHAT BEAT player ready — buttons active.")

# No infinite loop — player is fully event-driven for web server
