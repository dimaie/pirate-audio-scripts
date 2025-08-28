# web_server.py
from flask import Flask, request, jsonify
import threading
import player  # import the player module

app = Flask(__name__)

@app.route("/")
def index():
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

          async function setVolume() {{
            const vol = document.getElementById('volume_input').value;
            await fetch('/set_volume', {{
              method: 'POST',
              headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
              body: 'volume=' + encodeURIComponent(vol)
            }});
            document.getElementById('current_volume').innerText = vol;
          }}
        </script>
      </head>
      <body style="font-family:sans-serif; margin:2em;">
        <h2>Current Stream</h2>
        <p id="current_stream">{player.current_url}</p>
        <input type="text" id="stream_url" size="50" placeholder="Stream URL">
        <button onclick="setStream()">Set Stream</button>

        <h2>Volume</h2>
        <p id="current_volume">{player.current_volume}</p>
        <input type="number" id="volume_input" min="{player.VOLUME_MIN}" max="{player.VOLUME_MAX}" value="{player.current_volume}">
        <button onclick="setVolume()">Set Volume</button>
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
