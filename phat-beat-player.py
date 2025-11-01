#!/usr/bin/env python3
import vlc
import time
import json
import threading
import phatbeat_gpiozero as phatbeat
import os
import tempfile
import shutil
# ===============================
# Global variables and constants
# ===============================
config = None
stations = []
station_index = 0
current_url = None
current_label = None

instance = None
player = None
current_volume = 100
is_muted = False

timer_interval = 30
timer_enabled = False
timer_end = None
_timer_lock = threading.Lock()
initialized = False

# ---- Default Volume limits ----
VOLUME_MIN = 0
VOLUME_MAX = 200
VOLUME_STEP = 10
DEFAULT_VOLUME = 100

# ---- Button pin numbers (BCM) ----
BTN_REWIND = 13
BTN_FFWD = 5
BTN_PLAYPAUSE = 6
BTN_VOLUP = 16
BTN_VOLDN = 26
BTN_ONOFF = 12


# ===============================
# Initialization
# ===============================
def init(cfg):
    """Initialize player state and hardware, but do not start playback."""
    global config, stations, instance, player
    global VOLUME_MIN, VOLUME_MAX, VOLUME_STEP, DEFAULT_VOLUME
    global timer_interval, current_volume, initialized

    config = cfg

    # --- Load config values ---
    stations = config["stations"]
    VOLUME_MIN = config["volume"]["min"]
    VOLUME_MAX = config["volume"]["max"]
    VOLUME_STEP = config["volume"]["step"]
    DEFAULT_VOLUME = config["volume"]["default"]
    current_volume = DEFAULT_VOLUME
    timer_interval = config["timer"]["interval"]

    # --- Initialize hardware and VLC ---
    instance = vlc.Instance("--aout=alsa", "--alsa-audio-device=hw:1,0")
    player = instance.media_player_new()
    player.audio_set_volume(DEFAULT_VOLUME)

    # --- Clear LEDs ---
    phatbeat.clear()
    phatbeat.show()

    # --- Start timer thread ---
    threading.Thread(target=_monitor_timer, daemon=True).start()

    # --- Register button handlers ---
    phatbeat.on(BTN_FFWD)(handle_next)
    phatbeat.on(BTN_REWIND)(handle_prev)
    phatbeat.on(BTN_PLAYPAUSE)(handle_play_pause)
    phatbeat.on(BTN_VOLUP)(handle_vol_up)
    phatbeat.on(BTN_VOLDN)(handle_vol_down)
    phatbeat.on(BTN_ONOFF)(handle_timer)

    initialized = True
    print("pHAT BEAT player initialized — ready for playback.")
    start_playback()

def start_playback():
    """Begin playback of the first station after initialization."""
    if not initialized:
        raise RuntimeError("Player not initialized — call init(cfg) first.")

    global station_index
    station_index = 0
    play_stream(stations[station_index]["url"])
    print("Playback started.")


# ===============================
# LED helpers
# ===============================
def led_flash(color, duration=0.18):
    r, g, b = color
    phatbeat.set_all(r, g, b, brightness=0.5)
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


# ===============================
# Playback controls
# ===============================
def play_stream(url):
    global current_url, current_label
    if not initialized:
        raise RuntimeError("Player not initialized.")

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


def update_display():
    pass  # No display hardware

def save_config():
    """Persist current settings (volume, timer interval, stations) to config.json."""
    global config, current_volume, timer_interval, stations

    if config is None:
        print("Cannot save: configuration not loaded.")
        return False

    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    tmp_path = config_path + ".tmp"

    # Update config with current state
    config["volume"]["default"] = current_volume
    config["timer"]["interval"] = timer_interval
    config["stations"] = stations

    try:
        # Write atomically
        with open(tmp_path, "w") as f:
            json.dump(config, f, indent=2)
        shutil.move(tmp_path, config_path)
        print(f"Configuration saved to {config_path}")
        return True
    except Exception as e:
        print(f"Failed to save configuration: {e}")
        return False
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
# ===============================
# Timer logic
# ===============================
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

def set_timer_interval(minutes):
    """Update the sleep timer interval."""
    global timer_interval
    with _timer_lock:
        timer_interval = minutes
    print(f"Timer interval set to {minutes} minutes")


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


def get_timer_status():
    with _timer_lock:
        if timer_enabled and timer_end is not None:
            remaining = max(0, int((timer_end - time.time()) / 60))
            return f"ON ({remaining} min left)"
    return "OFF"


# ===============================
# Button callbacks
# ===============================
def handle_next(pin): next_station()
def handle_prev(pin): prev_station()
def handle_play_pause(pin): toggle_mute()
def handle_vol_up(pin): volume_up()
def handle_vol_down(pin): volume_down()
def handle_timer(pin): toggle_timer()
