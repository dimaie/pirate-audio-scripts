# web_server.py
from flask import Flask, request, jsonify
import threading
import player  # import the player module
import logging

app = Flask(__name__)

# Suppress werkzeug INFO logs for specific paths
class FilterPath(logging.Filter):
    def filter(self, record):
        # Suppress logging for /status, /set_volume, /set_url
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

    presets_html = "".join(
        f'<button onclick="setPreset(`{url}`)">{label}</button> '
        for label, url in presets
    )

    return f"""
    <html>
      <head>
        <title>Pirate Audio Control</title>
        <script>
          async function setStream() {{
            const url = document.getElementById('stream_url').value;
            await fetch('/set_url', {{
              method: 'POST',
              headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
              body: 'url=' + encodeURIComponent(url)
            }});
            document.getElementById('current_stream').innerText = url;
          }}

          async function setPreset(url) {{
            document.getElementById('stream_url').value = url;
            await setStream();
          }}

          async function setVolume(vol) {{
            await fetch('/set_volume', {{
              method: 'POST',
              headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
              body: 'volume=' + encodeURIComponent(vol)
            }});
            document.getElementById('current_volume').innerText = vol;
          }}

          function volumeChanged(e) {{
            const vol = e.target.value;
            document.getElementById('current_volume').innerText = vol;
            setVolume(vol);
          }}

          async function refreshStatus() {{
            try {{
              const res = await fetch('/status');
              const data = await res.json();
              document.getElementById('current_stream').innerText = data.url;
              document.getElementById('current_volume').innerText = data.volume;
              document.getElementById('volume_slider').value = data.volume;
            }} catch(e) {{
              console.error('Status fetch failed', e);
            }}
          }}

          setInterval(refreshStatus, 1000); // poll every second
        </script>
      </head>
      <body style="font-family:sans-serif; margin:2em;">
        <h2>Current Stream</h2>
        <p id="current_stream">{player.current_url}</p>
        <input type="text" id="stream_url" size="50" placeholder="Stream URL">
        <button onclick="setStream()">Set Stream</button>

        <h3>Presets</h3>
        {presets_html}

        <h2>Volume</h2>
        <p>Current: <span id="current_volume">{player.current_volume}</span></p>
        <input id="volume_slider" type="range" min="{player.VOLUME_MIN}" max="{player.VOLUME_MAX}" 
               value="{player.current_volume}" oninput="volumeChanged(event)">
      </body>
    </html>
    """

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
    # Keep main thread alive
    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        player.player.stop()
