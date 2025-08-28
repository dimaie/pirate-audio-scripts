# web_server.py
from flask import Flask, request, jsonify
import threading
import player  # import the player module

app = Flask(__name__)

@app.route("/")
def index():
    return f"""
    <html>
      <head><title>Pirate Audio Control</title></head>
      <body style="font-family:sans-serif; margin:2em;">
        <h2>Current Stream</h2>
        <p>{player.current_url}</p>
        <form action="/set_url" method="post">
          <input type="text" name="url" size="50" placeholder="Stream URL">
          <button type="submit">Set Stream</button>
        </form>
        <h2>Volume</h2>
        <p>Current: {player.current_volume}</p>
        <form action="/set_volume" method="post">
          <input type="number" name="volume" min="{player.VOLUME_MIN}" max="{player.VOLUME_MAX}" value="{player.current_volume}">
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
    player.play_stream(url)
    return f"Stream set to {url}", 200

@app.route("/set_volume", methods=["POST"])
def set_volume():
    try:
        vol = int(request.form.get("volume"))
    except (TypeError, ValueError):
        return "Invalid volume", 400
    player.current_volume = max(player.VOLUME_MIN, min(player.VOLUME_MAX, vol))
    player.player.audio_set_volume(player.current_volume)
    player.update_display()
    return f"Volume set to {player.current_volume}", 200

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
