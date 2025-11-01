async function addPreset() {
  const url = document.getElementById('stream_url').value.trim();
  if (!url) {
    alert('Please enter a stream URL first.');
    return;
  }

  const name = prompt('Enter a name for this station:');
  if (!name) return;

  try {
    const res = await fetch('/add_preset', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: new URLSearchParams({label: name, url: url})
    });

    if (res.ok) {
      alert('Preset added successfully.');

      // Add the new preset to the dropdown without reloading
      const select = document.getElementById('preset_select');
      const option = document.createElement('option');
      option.value = url;
      option.textContent = name;
      select.appendChild(option);

      // Optionally select the newly added one
      select.value = url;
    } else {
      const msg = await res.text();
      alert('Failed to add preset: ' + msg);
    }
  } catch (e) {
    console.error('Add preset failed:', e);
    alert('Error adding preset.');
  }
}

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

async function saveSettings() {
    try {
        const res = await fetch('/save_settings', { method: 'POST' });
        if (res.ok) {
            alert("Settings saved successfully!");
        } else {
            const text = await res.text();
            alert("Error saving settings: " + text);
        }
    } catch(e) {
        console.error('Save failed', e);
        alert('Save failed: ' + e.message);
    }
}

setInterval(refreshStatus, 1000); // poll every second
