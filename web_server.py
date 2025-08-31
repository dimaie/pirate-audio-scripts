from flask import Flask, request, jsonify, render_template
import threading
import player
import logging

app = Flask(__name__)

# Suppress werkzeug INFO logs for specific paths
class FilterPath(logging.Filter):
    def filter(self, record):
        if any(path in record.getMessage() for path in ['/status']):
            return False
        return True

werk_logger = logging.getLogger('werkzeug')
werk_logger.addFilter(FilterPath())

@app.route("/")
def index():
    return render_template(
        "index.html",
        presets=player.stations,        # reuse parsed stations
        current_url=player.current_url,
        current_volume=player.current_volume,
        volume_min=player.VOLUME_MIN,
        volume_max=player.VOLUME_MAX,
        muted=player.is_muted,
        timer_enabled=player.timer_enabled,
        timer_remaining=max(0, int((player.timer_end - time.time())/60)) if player.timer_enabled else None,
    )

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
        "timer_status": player.get_timer_status()  # e.g., "OFF" or "12 min"
    })

@app.route("/toggle_mute", methods=["POST"])
def toggle_mute_route():
    player.toggle_mute()  # call the function in player.py
    return "OK", 200

@app.route("/toggle_timer", methods=["POST"])
def toggle_timer_route():
    player.toggle_timer()
    return jsonify({"enabled": player.timer_enabled, "remaining": player.timer_remaining})

@app.route("/set_timer_interval", methods=["POST"])
def set_timer_interval_route():
    minutes = int(request.form["minutes"])
    player.set_timer_interval(minutes)
    return jsonify({"interval": player.timer_interval})

def run_web():
    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        player.player.stop()
