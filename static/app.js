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
  } catch (e) {
    console.error('Status fetch failed', e);
  }
}

setInterval(refreshStatus, 1000); // poll every second
