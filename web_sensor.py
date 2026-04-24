from flask import Flask, jsonify, render_template_string
import board, busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import time, threading

app = Flask(__name__)

i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)
channel = AnalogIn(ads, 0)

DRY_VALUE = 26170
WET_VALUE = 7470

status = {
    "state": "Unknown",
    "timestamp": "",
    "readings": 0,
    "changes": 0,
    "moisture_pct": 0,
    "uptime_start": time.time()
}

history = []

def get_percentage(raw):
    pct = (DRY_VALUE - raw) / (DRY_VALUE - WET_VALUE) * 100
    return max(0, min(100, round(pct, 1)))

def read_sensor():
    last_state = None
    while True:
        try:
            raw = channel.value
            pct = get_percentage(raw)

            if pct >= 60:
                state = "WET"
            elif pct >= 30:
                state = "MOIST"
            else:
                state = "DRY"

            status["moisture_pct"] = pct
            status["readings"] += 1

            history.append({
                "time": time.strftime("%H:%M:%S"),
                "pct": pct
            })
            if len(history) > 60:
                history.pop(0)

            if state != last_state:
                status["state"] = state
                status["timestamp"] = time.strftime("%H:%M:%S")
                status["changes"] += 1
                last_state = state

        except Exception as e:
            print("Sensor error:", e)
        time.sleep(2)

thread = threading.Thread(target=read_sensor, daemon=True)
thread.start()

HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Soil Monitor</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Segoe UI',Arial,sans-serif;background:#0d1117;color:#e6edf3;min-height:100vh;padding:24px 16px;}
@keyframes ripple{0%{transform:scale(0.8);opacity:1}100%{transform:scale(2.4);opacity:0}}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-10px)}}
@keyframes dropFall{0%{transform:translateY(-20px);opacity:0}60%{opacity:1}100%{transform:translateY(60px);opacity:0}}
@keyframes fadeInUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
@keyframes pulse-ring{0%{box-shadow:0 0 0 0 rgba(63,185,80,0.4)}100%{box-shadow:0 0 0 14px rgba(63,185,80,0)}}
@keyframes crackShift{0%,100%{transform:translateX(0)}50%{transform:translateX(2px)}}
@keyframes soilWave{0%{transform:translateX(0)}100%{transform:translateX(-50%)}}
.title-section{text-align:center;margin-bottom:24px;animation:fadeInUp 0.6s ease;}
.subtitle{font-size:11px;letter-spacing:3px;color:#7d8590;text-transform:uppercase;margin-bottom:6px;}
.title{font-size:22px;font-weight:600;}
.main-card{background:#161b22;border:1px solid #30363d;border-radius:16px;padding:32px 20px;text-align:center;margin-bottom:16px;animation:fadeInUp 0.6s ease 0.1s both;}
.gauge-wrap{position:relative;display:inline-block;margin-bottom:24px;}
.gauge-canvas{display:block;}
.gauge-center{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;}
.gauge-pct{font-size:32px;font-weight:700;line-height:1;}
.gauge-unit{font-size:12px;color:#7d8590;margin-top:4px;}
.ripple-ring{position:absolute;inset:-14px;border-radius:50%;border:2px solid #52b788;animation:ripple 1.8s ease-out infinite;pointer-events:none;}
.state-label{font-size:36px;font-weight:700;letter-spacing:4px;margin-bottom:8px;}
.state-sub{font-size:14px;color:#7d8590;margin-bottom:16px;}
.drops{display:flex;justify-content:center;gap:6px;margin-bottom:16px;}
.drop{width:8px;height:12px;border-radius:50% 50% 50% 50%/60% 60% 40% 40%;}
.soil-container{width:100%;height:60px;border-radius:10px;overflow:hidden;margin-bottom:0;position:relative;border:1px solid #30363d;}
.zone-labels{display:flex;justify-content:space-between;margin-top:6px;}
.zone-label{font-size:10px;color:#7d8590;}
.stats-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:16px;animation:fadeInUp 0.6s ease 0.2s both;}
.stat-card{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:14px 10px;text-align:center;}
.stat-label{font-size:10px;color:#7d8590;letter-spacing:1px;margin-bottom:6px;}
.stat-val{font-size:18px;font-weight:600;}
.graph-card{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:16px;margin-bottom:16px;animation:fadeInUp 0.6s ease 0.25s both;}
.graph-title{font-size:11px;color:#7d8590;letter-spacing:1px;margin-bottom:12px;}
.log-card{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:16px;animation:fadeInUp 0.6s ease 0.3s both;}
.log-title{font-size:11px;color:#7d8590;letter-spacing:1px;margin-bottom:12px;}
.log-entry{display:flex;align-items:center;gap:8px;font-size:12px;padding:4px 0;border-bottom:1px solid #21262d;}
.live-dot{display:inline-block;width:7px;height:7px;background:#3fb950;border-radius:50%;animation:pulse-ring 1.5s infinite;}
.footer{text-align:center;margin-top:14px;font-size:11px;color:#3fb950;display:flex;align-items:center;justify-content:center;gap:6px;}
</style>
</head>
<body>

<div class="title-section">
  <div class="subtitle">Raspberry Pi 5 · Live Monitor</div>
  <div class="title">Soil Moisture Dashboard</div>
</div>

<div class="main-card">

  <!-- Circular gauge -->
  <div class="gauge-wrap" id="gauge-wrap">
    <div class="ripple-ring" id="ripple-ring"></div>
    <canvas class="gauge-canvas" id="gaugeCanvas" width="180" height="180"></canvas>
    <div class="gauge-center">
      <div class="gauge-pct" id="gauge-pct" style="color:#52b788;">--%</div>
      <div class="gauge-unit">moisture</div>
    </div>
  </div>

  <div class="state-label" id="state-label">--</div>
  <div class="state-sub" id="state-sub">Connecting to sensor...</div>

  <div class="drops" id="drops" style="display:none;">
    <div class="drop" style="background:#52b788;animation:dropFall 1.4s ease-in infinite;"></div>
    <div class="drop" style="background:#52b788;animation:dropFall 1.4s ease-in 0.4s infinite;"></div>
    <div class="drop" style="background:#52b788;animation:dropFall 1.4s ease-in 0.8s infinite;"></div>
  </div>

  <!-- Animated soil illustration -->
  <div class="soil-container" id="soil-container">
    <canvas id="soilCanvas" width="600" height="60" style="width:100%;height:100%;display:block;"></canvas>
  </div>
  <div class="zone-labels">
    <span class="zone-label" style="color:#e07a5f;">DRY 0–30%</span>
    <span class="zone-label" style="color:#EF9F27;">MOIST 30–60%</span>
    <span class="zone-label" style="color:#52b788;">WET 60–100%</span>
  </div>
</div>

<div class="stats-grid">
  <div class="stat-card"><div class="stat-label">UPTIME</div><div class="stat-val" id="uptime">--:--:--</div></div>
  <div class="stat-card"><div class="stat-label">READINGS</div><div class="stat-val" id="readings">0</div></div>
  <div class="stat-card"><div class="stat-label">CHANGES</div><div class="stat-val" id="changes">0</div></div>
</div>

<!-- History graph -->
<div class="graph-card">
  <div class="graph-title">MOISTURE HISTORY (last 30 readings)</div>
  <canvas id="historyChart" height="120"></canvas>
</div>

<div class="log-card">
  <div class="log-title">ACTIVITY LOG</div>
  <div id="log"><div style="font-size:12px;color:#7d8590;">Waiting for sensor changes...</div></div>
</div>

<div class="footer">
  <span class="live-dot"></span>
  Live · raspberrypi.local:5000
</div>

<script>
let lastState = null;
let audioCtx = null;
let historyChart = null;
let gaugeCtx = null;
let soilCtx = null;
let soilOffset = 0;
let currentPct = 0;
let targetPct = 0;

function getColor(state){
  if(state==='WET') return '#52b788';
  if(state==='MOIST') return '#EF9F27';
  return '#e07a5f';
}

function getMessage(state){
  if(state==='WET') return 'Soil is well watered!';
  if(state==='MOIST') return 'Soil moisture is adequate.';
  return 'Please water your plant soon!';
}

function getIconBg(state){
  if(state==='WET') return {bg:'#1e3a2f',border:'#2d6a4f'};
  if(state==='MOIST') return {bg:'#2e2510',border:'#5a4010'};
  return {bg:'#3a1e1e',border:'#6a2d2d'};
}

// --- Circular gauge ---
function initGauge(){
  const canvas = document.getElementById('gaugeCanvas');
  gaugeCtx = canvas.getContext('2d');
}

function drawGauge(pct, color){
  if(!gaugeCtx) return;
  const cx = 90, cy = 90, r = 70;
  const startAngle = Math.PI * 0.75;
  const fullAngle = Math.PI * 1.5;
  const endAngle = startAngle + (pct / 100) * fullAngle;

  gaugeCtx.clearRect(0, 0, 180, 180);

  gaugeCtx.beginPath();
  gaugeCtx.arc(cx, cy, r, startAngle, startAngle + fullAngle);
  gaugeCtx.strokeStyle = '#21262d';
  gaugeCtx.lineWidth = 14;
  gaugeCtx.lineCap = 'round';
  gaugeCtx.stroke();

  if(pct > 0){
    gaugeCtx.beginPath();
    gaugeCtx.arc(cx, cy, r, startAngle, endAngle);
    gaugeCtx.strokeStyle = color;
    gaugeCtx.lineWidth = 14;
    gaugeCtx.lineCap = 'round';
    gaugeCtx.stroke();
  }

  gaugeCtx.beginPath();
  gaugeCtx.arc(cx, cy, r - 20, 0, Math.PI * 2);
  gaugeCtx.fillStyle = '#0d1117';
  gaugeCtx.fill();
}

// --- Soil animation ---
function initSoil(){
  const canvas = document.getElementById('soilCanvas');
  soilCtx = canvas.getContext('2d');
  animateSoil();
}

function drawSoilFrame(pct){
  if(!soilCtx) return;
  const w = 600, h = 60;
  soilCtx.clearRect(0, 0, w, h);

  const wetness = pct / 100;
  const r1 = Math.round(80 + (20 - 80) * wetness);
  const g1 = Math.round(50 + (100 - 50) * wetness);
  const b1 = Math.round(20 + (60 - 20) * wetness);
  const baseColor = `rgb(${r1},${g1},${b1})`;

  soilCtx.fillStyle = baseColor;
  soilCtx.fillRect(0, 0, w, h);

  if(wetness > 0.3){
    const waveCount = 3;
    const waveH = 6 * wetness;
    soilCtx.fillStyle = `rgba(30,180,120,${0.15 * wetness})`;
    for(let i = 0; i < waveCount; i++){
      soilCtx.beginPath();
      const offset = (soilOffset * (1 + i * 0.3)) % (w * 2);
      for(let x = -w; x < w * 2; x += 4){
        const y = h * 0.5 + Math.sin((x + offset) * 0.04 + i * 2) * waveH;
        if(x === -w) soilCtx.moveTo(x, y);
        else soilCtx.lineTo(x, y);
      }
      soilCtx.lineTo(w * 2, h);
      soilCtx.lineTo(-w, h);
      soilCtx.closePath();
      soilCtx.fill();
    }
  }

  if(wetness < 0.4){
    soilCtx.strokeStyle = `rgba(180,120,60,${0.4 * (1 - wetness * 2)})`;
    soilCtx.lineWidth = 1;
    const cracks = [[60,10,80,40],[150,5,140,50],[250,15,270,45],[380,8,360,52],[480,12,500,42],[550,20,530,50]];
    cracks.forEach(([x1,y1,x2,y2]) => {
      soilCtx.beginPath();
      soilCtx.moveTo(x1, y1);
      soilCtx.lineTo(x1 + (x2-x1)*0.5 + 5, y1 + (y2-y1)*0.5);
      soilCtx.lineTo(x2, y2);
      soilCtx.stroke();
    });
  }

  const particles = 12;
  for(let i = 0; i < particles; i++){
    const px = (i * 47 + 20) % w;
    const py = (i * 31 + 10) % h;
    const pr = 2 + (i % 3);
    const darkness = 0.15 + (i % 4) * 0.05;
    soilCtx.beginPath();
    soilCtx.arc(px, py, pr, 0, Math.PI * 2);
    soilCtx.fillStyle = `rgba(0,0,0,${darkness})`;
    soilCtx.fill();
  }
}

function animateSoil(){
  soilOffset += 0.5;
  drawSoilFrame(currentPct);
  requestAnimationFrame(animateSoil);
}

// smooth gauge animation
function animateGauge(){
  if(Math.abs(currentPct - targetPct) > 0.2){
    currentPct += (targetPct - currentPct) * 0.05;
    const state = document.getElementById('state-label').textContent;
    drawGauge(currentPct, getColor(state));
  }
  requestAnimationFrame(animateGauge);
}

// --- Sound alert ---
function playDryAlert(){
  try {
    if(!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const times = [0, 0.3, 0.6];
    times.forEach(t => {
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.frequency.setValueAtTime(880, audioCtx.currentTime + t);
      osc.frequency.exponentialRampToValueAtTime(440, audioCtx.currentTime + t + 0.2);
      gain.gain.setValueAtTime(0.3, audioCtx.currentTime + t);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + t + 0.25);
      osc.start(audioCtx.currentTime + t);
      osc.stop(audioCtx.currentTime + t + 0.25);
    });
  } catch(e){}
}

function playWetAlert(){
  try {
    if(!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    [523, 659, 784].forEach((freq, i) => {
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.frequency.value = freq;
      gain.gain.setValueAtTime(0.2, audioCtx.currentTime + i * 0.15);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + i * 0.15 + 0.3);
      osc.start(audioCtx.currentTime + i * 0.15);
      osc.stop(audioCtx.currentTime + i * 0.15 + 0.3);
    });
  } catch(e){}
}

// --- History chart ---
function initChart(){
  const ctx = document.getElementById('historyChart').getContext('2d');
  historyChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label: 'Moisture %',
        data: [],
        borderColor: '#52b788',
        backgroundColor: 'rgba(82,183,136,0.08)',
        borderWidth: 2,
        pointRadius: 2,
        pointBackgroundColor: '#52b788',
        tension: 0.4,
        fill: true
      }]
    },
    options: {
      responsive: true,
      animation: { duration: 500 },
      scales: {
        x: {
          ticks: { color:'#7d8590', font:{size:10}, maxTicksLimit:6 },
          grid: { color:'#21262d' }
        },
        y: {
          min: 0, max: 100,
          ticks: { color:'#7d8590', font:{size:10}, callback: v => v+'%' },
          grid: { color:'#21262d' }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: { label: ctx => ctx.parsed.y.toFixed(1) + '%' }
        }
      }
    }
  });
}

function updateChart(history){
  if(!historyChart) return;
  const last30 = history.slice(-30);
  historyChart.data.labels = last30.map(h => h.time);
  historyChart.data.datasets[0].data = last30.map(h => h.pct);

  const avg = last30.reduce((a,b) => a + b.pct, 0) / (last30.length || 1);
  let chartColor = '#52b788';
  if(avg < 30) chartColor = '#e07a5f';
  else if(avg < 60) chartColor = '#EF9F27';
  historyChart.data.datasets[0].borderColor = chartColor;
  historyChart.data.datasets[0].pointBackgroundColor = chartColor;
  historyChart.data.datasets[0].backgroundColor = chartColor + '14';
  historyChart.update();
}

// --- Main update ---
function updateUI(data){
  const state = data.state;
  const unknown = state === 'Unknown';
  const color = getColor(state);
  const pct = data.moisture_pct;

  targetPct = pct;

  document.getElementById('state-label').textContent = state;
  document.getElementById('state-label').style.color = unknown ? '#7d8590' : color;
  document.getElementById('state-sub').textContent = unknown ? 'Connecting...' : getMessage(state);
  document.getElementById('ripple-ring').style.borderColor = color;
  document.getElementById('gauge-pct').textContent = pct + '%';
  document.getElementById('gauge-pct').style.color = color;
  document.getElementById('drops').style.display = state==='WET' ? 'flex' : 'none';

  document.getElementById('readings').textContent = data.readings;
  document.getElementById('changes').textContent = data.changes;

  const sec = Math.floor(data.uptime);
  const h = String(Math.floor(sec/3600)).padStart(2,'0');
  const m = String(Math.floor((sec%3600)/60)).padStart(2,'0');
  const s = String(sec%60).padStart(2,'0');
  document.getElementById('uptime').textContent = h+':'+m+':'+s;

  if(state !== lastState && !unknown && data.timestamp){
    if(state === 'DRY') playDryAlert();
    else if(state === 'WET') playWetAlert();

    lastState = state;
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.innerHTML = '<span style="font-weight:600;color:'+color+';">'+state+'</span><span style="color:#30363d;">|</span><span style="color:#7d8590;">'+data.timestamp+'</span><span style="color:#7d8590;margin-left:auto;">'+pct+'% moisture</span>';
    const logEl = document.getElementById('log');
    if(logEl.children.length===1 && !logEl.children[0].className) logEl.innerHTML='';
    logEl.insertBefore(entry, logEl.firstChild);
    if(logEl.children.length>5) logEl.removeChild(logEl.lastChild);
  }
}

function fetchData(){
  fetch('/api')
    .then(r=>r.json())
    .then(data=>{
      updateUI(data);
      if(data.history) updateChart(data.history);
    })
    .catch(()=>{});
}

initGauge();
initSoil();
initChart();
animateGauge();
fetchData();
setInterval(fetchData, 2000);
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/api")
def api():
    return jsonify({
        "state": status["state"],
        "timestamp": status["timestamp"],
        "readings": status["readings"],
        "changes": status["changes"],
        "moisture_pct": status["moisture_pct"],
        "uptime": time.time() - status["uptime_start"],
        "history": history
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)