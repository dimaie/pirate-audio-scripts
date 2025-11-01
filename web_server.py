import threading
import time
import logging
import json
import importlib
from flask import Flask, request, jsonify, render_template
import os

app = Flask(__name__)

# ---- Load configuration ----
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

PLAYER_MODULE_NAME = config.get("player_module", "player")
player = importlib.import_module(PLAYER_MODULE_NAME)

# ---- Detect if player supports saving configuration ----
supports_save = hasattr(player, "save_config")
# Determine which player to load
PLAYER_MODULE_NAME = config.get("player_module", "player")  # default to 'player'
player = importlib.import_module(PLAYER_MODULE_NAME)

player.init(config)

# ---- Suppress werkzeug INFO logs for specific paths ----
class FilterPath(logging.Filter):
    def filter(self, record):
        if any(path in record.getMessage() for path in ['/status']):
            return False
        return True

werk_logger = logging.getLogger('werkzeug')
werk_logger.addFilter(FilterPath())

# ---- Flask routes ----

@app.route("/")
def index():
    remaining = None
    if player.timer_enabled and player.timer_end is not None:
        remaining = max(0, int((player.timer_end - time.time()) / 60))

    return render_template(
        "index.html",
        presets=getattr(player, "stations", []),
        current_url=getattr(player, "current_url", ""),
        current_volume=getattr(player, "current_volume", 0),
        volume_min=getattr(player, "VOLUME_MIN", 0),
        volume_max=getattr(player, "VOLUME_MAX", 100),
        muted=getattr(player, "is_muted", False),
        timer_enabled=getattr(player, "timer_enabled", False),
        timer_remaining=remaining,
        supports_save=supports_save
    )

# In Flask route
@app.route("/add_preset", methods=["POST"])
def add_preset():
    label = request.form.get("label")
    url = request.form.get("url")
    if not label or not url:
        return "Missing label or URL", 400

    # avoid duplicates
    if any(s["url"] == url for s in config["stations"]):
        return "Preset already exists", 409

    config["stations"].append({"label": label, "url": url})
    if hasattr(player, "save_config"):
        player.save_config()
    return "OK", 200

@app.route("/set_url", methods=["POST"])
def set_url():
    url = request.form.get("url")
    if not url:
        return "Missing url", 400
    player.play_stream(url)
    return "OK", 200

@app.route("/set_volume", methods=["POST"])
def set_volume():
    try:
        vol = int(request.form.get("volume"))
    except (TypeError, ValueError):
        return "Invalid volume", 400
    player.current_volume = max(player.VOLUME_MIN, min(player.VOLUME_MAX, vol))
    player.player.audio_set_volume(player.current_volume)
    player.update_display()
    return "OK", 200

@app.route("/status")
def status():
    return jsonify({
        "url": player.current_url,
        "volume": player.current_volume,
        "muted": player.is_muted,
        "timer_status": player.get_timer_status()
    })

@app.route("/toggle_mute", methods=["POST"])
def toggle_mute_route():
    player.toggle_mute()
    return "OK", 200

@app.route("/toggle_timer", methods=["POST"])
def toggle_timer_route():
    player.toggle_timer()
    remaining = None
    if player.timer_enabled and player.timer_end is not None:
        remaining = max(0, int((player.timer_end - time.time()) / 60))
    return jsonify({"enabled": player.timer_enabled, "remaining": remaining})

@app.route("/set_timer_interval", methods=["POST"])
def set_timer_interval_route():
    minutes = int(request.form["minutes"])
    player.set_timer_interval(minutes)
    return jsonify({"interval": player.timer_interval})

@app.route("/save_settings", methods=["POST"])
def save_settings():
    if not supports_save:
        return "Save not supported", 400
    try:
        # optional: pass the current config or player state
        player.save_config()
        return "Settings saved", 200
    except Exception as e:
        return f"Error saving settings: {e}", 500

# ---- Web server thread ----
def run_web():
    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        player.player.stop()
