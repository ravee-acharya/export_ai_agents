"""
3D Trade Routes Globe.

The signature visual of the ExportAI dashboard: an interactive 3D
globe (Three.js, rendered via streamlit.components.v1.html) centered
on India, with animated arcs flying to each target market. Arc color
encodes opportunity score (teal = strong, brass = moderate, coral =
weak); destination markers scale with score. Drag to rotate, scroll
to zoom.

Design notes / constraints:
- Three.js is loaded from cdnjs (the CDN Streamlit component iframes
  can reach). If the user is offline, the component degrades to a
  short text note rather than a broken canvas.
- Rendered inside an iframe by Streamlit, so it can't read app state
  directly -- everything it needs is serialized into the HTML at
  render time (market list with lat/lon/score).
- Country coordinates are a small built-in table; unknown countries
  are skipped silently rather than plotted at (0,0) in the Atlantic.
"""

import json

import streamlit.components.v1 as components

# Approximate centroid coordinates for supported markets.
_COUNTRY_COORDS = {
    "IN": (20.6, 78.9),   # India -- origin of all arcs
    "US": (39.8, -98.6),
    "DE": (51.2, 10.4),
    "GB": (54.0, -2.5),
    "CA": (56.1, -106.3),
    "AU": (-25.3, 133.8),
    "AE": (24.0, 54.0),
    "SG": (1.35, 103.8),
    "JP": (36.2, 138.3),
    "FR": (46.6, 2.2),
    "IT": (42.8, 12.8),
    "ES": (40.5, -3.7),
    "NL": (52.1, 5.3),
    "BE": (50.6, 4.5),
}


def _score_color(score: float) -> str:
    if score >= 60:
        return "#3FB8AF"  # teal -- strong
    if score >= 30:
        return "#E3A857"  # brass -- moderate
    return "#E2725B"      # coral -- weak


def render_trade_globe(opportunity_scores: list[dict], height: int = 420) -> None:
    """
    Render the globe. Takes the same opportunity_scores list the rest
    of the dashboard uses; aggregates to one best score per country.
    Renders nothing (silently) if no scored country has coordinates.
    """
    best_per_country: dict[str, float] = {}
    for s in opportunity_scores or []:
        country = s.get("destination_country", "").upper()
        score = float(s.get("score", 0))
        if country in _COUNTRY_COORDS:
            best_per_country[country] = max(best_per_country.get(country, 0), score)

    if not best_per_country:
        return

    markets = [
        {
            "code": code,
            "lat": _COUNTRY_COORDS[code][0],
            "lon": _COUNTRY_COORDS[code][1],
            "score": score,
            "color": _score_color(score),
        }
        for code, score in best_per_country.items()
    ]

    origin = {"lat": _COUNTRY_COORDS["IN"][0], "lon": _COUNTRY_COORDS["IN"][1]}

    html = _GLOBE_TEMPLATE.replace("__MARKETS__", json.dumps(markets)).replace(
        "__ORIGIN__", json.dumps(origin)
    )

    components.html(html, height=height)


_GLOBE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<style>
  html, body { margin: 0; padding: 0; background: transparent; overflow: hidden; }
  #globe-wrap { width: 100%; height: 100vh; position: relative; }
  #legend {
    position: absolute; bottom: 10px; left: 12px;
    font-family: Arial, sans-serif; font-size: 11px; color: #9CA3BF;
    background: rgba(13,18,32,0.75); border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px; padding: 7px 10px; line-height: 1.7;
  }
  #legend .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 5px; }
  #hint {
    position: absolute; top: 10px; right: 12px;
    font-family: Arial, sans-serif; font-size: 10.5px; color: #9CA3BF;
    background: rgba(13,18,32,0.75); border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px; padding: 5px 9px;
  }
  #fallback {
    display: none; color: #9CA3BF; font-family: Arial, sans-serif;
    font-size: 12px; padding: 20px; text-align: center;
  }
</style>
</head>
<body>
<div id="globe-wrap">
  <div id="legend">
    <span class="dot" style="background:#3FB8AF"></span>Strong opportunity<br>
    <span class="dot" style="background:#E3A857"></span>Moderate<br>
    <span class="dot" style="background:#E2725B"></span>Weak
  </div>
  <div id="hint">Drag to rotate &middot; scroll to zoom</div>
  <div id="fallback">3D globe unavailable (couldn't load the graphics library). Your data is unaffected.</div>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
if (typeof THREE === 'undefined') {
  document.getElementById('fallback').style.display = 'block';
  document.getElementById('legend').style.display = 'none';
  document.getElementById('hint').style.display = 'none';
} else {

const MARKETS = __MARKETS__;
const ORIGIN = __ORIGIN__;

const wrap = document.getElementById('globe-wrap');
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45, wrap.clientWidth / wrap.clientHeight, 0.1, 1000);
camera.position.set(0, 1.2, 4.6);

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setSize(wrap.clientWidth, wrap.clientHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
wrap.appendChild(renderer.domElement);

const globeGroup = new THREE.Group();
scene.add(globeGroup);

// ---- Sphere: dark ocean with subtle wireframe graticule ----
const sphereGeo = new THREE.SphereGeometry(1.6, 48, 48);
const sphereMat = new THREE.MeshPhongMaterial({
  color: 0x161d33, emissive: 0x0a0f1e, shininess: 12,
  transparent: true, opacity: 0.96
});
globeGroup.add(new THREE.Mesh(sphereGeo, sphereMat));

const gratMat = new THREE.LineBasicMaterial({ color: 0x2a3355, transparent: true, opacity: 0.5 });
for (let latDeg = -60; latDeg <= 60; latDeg += 30) {
  const pts = [];
  const r = 1.602 * Math.cos(latDeg * Math.PI / 180);
  const y = 1.602 * Math.sin(latDeg * Math.PI / 180);
  for (let i = 0; i <= 72; i++) {
    const a = (i / 72) * Math.PI * 2;
    pts.push(new THREE.Vector3(r * Math.cos(a), y, r * Math.sin(a)));
  }
  globeGroup.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), gratMat));
}
for (let lonDeg = 0; lonDeg < 180; lonDeg += 30) {
  const pts = [];
  for (let i = 0; i <= 72; i++) {
    const a = (i / 72) * Math.PI * 2;
    const v = latLonToVec(90 - (i / 72) * 180, lonDeg, 1.602);
    pts.push(v);
  }
  // full meridian circle: go down one side, up the other
  const pts2 = [];
  for (let i = 0; i <= 144; i++) {
    const lat = 90 - (i / 144) * 360;
    const normLat = lat < -90 ? -180 - lat : lat;
    const lon = lat < -90 ? lonDeg + 180 : lonDeg;
    pts2.push(latLonToVec(normLat, lon, 1.602));
  }
  globeGroup.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts2), gratMat));
}

function latLonToVec(lat, lon, radius) {
  const phi = (90 - lat) * Math.PI / 180;
  const theta = (lon + 180) * Math.PI / 180;
  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta)
  );
}

// ---- Origin marker: India, brass pulse ----
const originPos = latLonToVec(ORIGIN.lat, ORIGIN.lon, 1.62);
const originMarker = new THREE.Mesh(
  new THREE.SphereGeometry(0.045, 16, 16),
  new THREE.MeshBasicMaterial({ color: 0xE3A857 })
);
originMarker.position.copy(originPos);
globeGroup.add(originMarker);

const originHalo = new THREE.Mesh(
  new THREE.RingGeometry(0.06, 0.085, 32),
  new THREE.MeshBasicMaterial({ color: 0xE3A857, transparent: true, opacity: 0.6, side: THREE.DoubleSide })
);
originHalo.position.copy(originPos);
originHalo.lookAt(originPos.clone().multiplyScalar(2));
globeGroup.add(originHalo);

// ---- Destination markers + arcs ----
const arcData = [];
MARKETS.forEach(m => {
  const destPos = latLonToVec(m.lat, m.lon, 1.62);
  const size = 0.03 + (m.score / 100) * 0.05;
  const marker = new THREE.Mesh(
    new THREE.SphereGeometry(size, 16, 16),
    new THREE.MeshBasicMaterial({ color: new THREE.Color(m.color) })
  );
  marker.position.copy(destPos);
  globeGroup.add(marker);

  // Great-circle-ish arc via quadratic-lifted midpoint
  const mid = originPos.clone().add(destPos).multiplyScalar(0.5);
  const lift = 1.62 + originPos.distanceTo(destPos) * 0.35;
  mid.normalize().multiplyScalar(lift);
  const curve = new THREE.QuadraticBezierCurve3(originPos, mid, destPos);
  const pts = curve.getPoints(60);
  const arcGeo = new THREE.BufferGeometry().setFromPoints(pts);
  const arcMat = new THREE.LineBasicMaterial({
    color: new THREE.Color(m.color), transparent: true, opacity: 0.75
  });
  globeGroup.add(new THREE.Line(arcGeo, arcMat));

  // Moving pulse dot along the arc
  const pulse = new THREE.Mesh(
    new THREE.SphereGeometry(0.022, 8, 8),
    new THREE.MeshBasicMaterial({ color: new THREE.Color(m.color) })
  );
  globeGroup.add(pulse);
  arcData.push({ curve: curve, pulse: pulse, offset: Math.random() });
});

// ---- Lights ----
scene.add(new THREE.AmbientLight(0xffffff, 0.55));
const key = new THREE.DirectionalLight(0x3fb8af, 0.5);
key.position.set(4, 3, 5);
scene.add(key);
const rim = new THREE.DirectionalLight(0xe3a857, 0.35);
rim.position.set(-4, -1, -3);
scene.add(rim);

// ---- Interaction: drag to rotate, scroll to zoom ----
let isDragging = false, prevX = 0, prevY = 0;
let rotY = -1.2, rotX = 0.25;   // start centered roughly on India
let targetRotY = rotY, targetRotX = rotX;
let autoSpin = true;

renderer.domElement.addEventListener('mousedown', e => {
  isDragging = true; autoSpin = false; prevX = e.clientX; prevY = e.clientY;
});
window.addEventListener('mouseup', () => { isDragging = false; });
window.addEventListener('mousemove', e => {
  if (!isDragging) return;
  targetRotY += (e.clientX - prevX) * 0.005;
  targetRotX += (e.clientY - prevY) * 0.003;
  targetRotX = Math.max(-1.2, Math.min(1.2, targetRotX));
  prevX = e.clientX; prevY = e.clientY;
});
renderer.domElement.addEventListener('wheel', e => {
  e.preventDefault();
  camera.position.multiplyScalar(1 + Math.sign(e.deltaY) * 0.06);
  const d = camera.position.length();
  if (d < 2.6) camera.position.setLength(2.6);
  if (d > 8) camera.position.setLength(8);
}, { passive: false });

// Touch support
renderer.domElement.addEventListener('touchstart', e => {
  if (e.touches.length === 1) {
    isDragging = true; autoSpin = false;
    prevX = e.touches[0].clientX; prevY = e.touches[0].clientY;
  }
}, { passive: true });
window.addEventListener('touchend', () => { isDragging = false; }, { passive: true });
window.addEventListener('touchmove', e => {
  if (!isDragging || e.touches.length !== 1) return;
  targetRotY += (e.touches[0].clientX - prevX) * 0.005;
  targetRotX += (e.touches[0].clientY - prevY) * 0.003;
  targetRotX = Math.max(-1.2, Math.min(1.2, targetRotX));
  prevX = e.touches[0].clientX; prevY = e.touches[0].clientY;
}, { passive: true });

// ---- Animate ----
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
let t = 0;
function animate() {
  requestAnimationFrame(animate);
  t += 0.008;

  if (autoSpin && !reduceMotion) targetRotY += 0.0012;
  rotY += (targetRotY - rotY) * 0.08;
  rotX += (targetRotX - rotX) * 0.08;
  globeGroup.rotation.y = rotY;
  globeGroup.rotation.x = rotX;

  if (!reduceMotion) {
    const s = 1 + Math.sin(t * 3) * 0.25;
    originHalo.scale.set(s, s, s);
    arcData.forEach(a => {
      const p = a.curve.getPoint((t * 0.35 + a.offset) % 1);
      a.pulse.position.copy(p);
    });
  }

  renderer.render(scene, camera);
}
animate();

window.addEventListener('resize', () => {
  camera.aspect = wrap.clientWidth / wrap.clientHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(wrap.clientWidth, wrap.clientHeight);
});

}
</script>
</body>
</html>
"""
