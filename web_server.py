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
    presets = [
        ("BBC World Service", "http://stream.live.vc.bbcmedia.co.uk/bbc_world_service"),
        ("NPR News", "https://npr-ice.streamguys1.com/live.mp3"),
        ("Radio Swiss Classic", "http://stream.srg-ssr.ch/m/rsc_de/mp3_128"),
        ("Classic FM UK", "http://media-ice.musicradio.com/ClassicFMMP3")
    ]
    return render_template(
        "index.html",
        presets=presets,
        current_url=player.current_url,
        current_volume=player.current_volume,
        volume_min=player.VOLUME_MIN,
        volume_max=player.VOLUME_MAX,
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
    return jsonify({"url": player.current_url, "volume": player.current_volume})

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
