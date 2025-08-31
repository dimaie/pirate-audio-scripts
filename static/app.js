function toggleTimer() {
  fetch('/toggle_timer', {method: 'POST'})
    .then(res => res.json())
    .then(data => console.log("Timer:", data));
}

function setTimerInterval() {
  const minutes = document.getElementById('timerInterval').value;
  fetch('/set_timer_interval', {
    method: 'POST',
    body: new URLSearchParams({minutes: minutes}),
    headers: {'Content-Type': 'application/x-www-form-urlencoded'}
  }).then(res => res.json())
    .then(data => console.log("Interval set:", data));
}

async function toggleMute() {
    await fetch('/toggle_mute', { method: 'POST' });
    await refreshStatus();
}

async function setStream() {
  const url = document.getElementById('stream_url').value;
  await fetch('/set_url', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'url=' + encodeURIComponent(url)
  });
  document.getElementById('current_stream').innerText = url;
}

async function setPreset(url) {
  document.getElementById('stream_url').value = url;
  await setStream();
}

async function setVolume(vol) {
  await fetch('/set_volume', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'volume=' + encodeURIComponent(vol)
  });
  document.getElementById('current_volume').innerText = vol;
}

function volumeChanged(e) {
  const vol = e.target.value;
  document.getElementById('current_volume').innerText = vol;
  setVolume(vol);
}

async function refreshStatus() {
    try {
        const res = await fetch('/status');
        const data = await res.json();
        document.getElementById('current_stream').innerText = data.url;
        document.getElementById('current_volume').innerText = data.volume;
        document.getElementById('volume_slider').value = data.volume;
        document.getElementById('mute_state').innerText = data.muted ? "ON" : "OFF";
        document.getElementById('timer-status').innerText =
            'Timer: ' + data.timer_status;
    } catch(e) {
        console.error('Status fetch failed', e);
    }
}

setInterval(refreshStatus, 1000); // poll every second
