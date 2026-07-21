"""
3D interactive app background.

Uses streamlit.components.v1.html — available in ALL Streamlit versions
(stable since 0.x, no unsafe_allow_javascript needed).

How it works:
- components.v1.html renders a sandboxed srcdoc iframe
- Sandbox includes allow-same-origin + allow-scripts, so the script
  inside CAN reach window.parent.document (srcdoc = same origin)
- body{height:0;overflow:hidden} makes the iframe auto-resize to 0px
  via the built-in MutationObserver postMessage — no external CSS needed
- Script injects a fixed-position canvas into window.parent.document
  then loads Three.js and starts the particle animation
- Double-injection guard prevents re-running on Streamlit reruns
"""

import streamlit as st

# Injected into window.parent (the real Streamlit page) via srcdoc iframe
_CSS_FOR_PARENT = """
  .stApp { position: relative; }
  #exportai-bg {
    position: fixed !important;
    inset: 0 !important;
    width: 100vw !important;
    height: 100vh !important;
    z-index: -1 !important;
    pointer-events: none !important;
    display: block !important;
  }
  [data-testid="stBottom"] {
    position: relative !important;
    z-index: 100 !important;
    background: rgba(13,18,32,0.85) !important;
    backdrop-filter: blur(8px) !important;
  }
"""

_HTML = """
<!DOCTYPE html>
<html>
<head>
<style>
  /* Zero-height body so the iframe auto-resizes to 0px */
  html, body { margin: 0; padding: 0; height: 0; overflow: hidden; }
</style>
</head>
<body>
<script>
(function() {
  // Double-injection guard: safe to call on every Streamlit rerun
  var doc = document;
  if (doc.getElementById('exportai-bg')) return;

  // 1. Inject CSS into parent page
  var style = doc.createElement('style');
  style.textContent = `CSS_PLACEHOLDER`;
  doc.head.appendChild(style);

  // 2. Create canvas in parent body
  var canvas = doc.createElement('canvas');
  canvas.id = 'exportai-bg';
  doc.body.insertBefore(canvas, doc.body.firstChild);

  // 3. Load Three.js into parent window, then animate
  var script = doc.createElement('script');
  script.src = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js';
  script.onload = function() { startScene(window.THREE, doc, canvas); };
  script.onerror = function() {
    // CDN unreachable — remove canvas, app still works perfectly
    var c = doc.getElementById('exportai-bg');
    if (c) c.remove();
  };
  doc.head.appendChild(script);

  function startScene(THREE, doc, canvas) {
    if (!THREE) return;
    var win = window;
    var reduceMotion = win.matchMedia('(prefers-reduced-motion: reduce)').matches;

    var renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(win.devicePixelRatio || 1, 1.5));
    renderer.setSize(win.innerWidth, win.innerHeight);

    var scene = new THREE.Scene();
    var camera = new THREE.PerspectiveCamera(60, win.innerWidth / win.innerHeight, 1, 1000);
    camera.position.z = 220;

    // Particle field
    var COUNT = 480;
    var pos = new Float32Array(COUNT * 3);
    var col = new Float32Array(COUNT * 3);
    var spd = new Float32Array(COUNT);
    var brass = new THREE.Color('#E3A857');
    var teal  = new THREE.Color('#3FB8AF');

    for (var i = 0; i < COUNT; i++) {
      pos[i*3]   = (Math.random() - 0.5) * 900;
      pos[i*3+1] = (Math.random() - 0.5) * 500;
      pos[i*3+2] = (Math.random() - 0.5) * 300;
      var c = Math.random() < 0.4 ? brass : teal;
      col[i*3] = c.r; col[i*3+1] = c.g; col[i*3+2] = c.b;
      spd[i] = 0.12 + Math.random() * 0.28;
    }

    var geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geo.setAttribute('color',    new THREE.BufferAttribute(col, 3));
    var mat = new THREE.PointsMaterial({
      size: 2.4, vertexColors: true,
      transparent: true, opacity: 0.5,
      depthWrite: false, blending: THREE.AdditiveBlending
    });
    scene.add(new THREE.Points(geo, mat));

    // Connecting lines
    var MAX_L = 80;
    var lpos = new Float32Array(MAX_L * 6);
    var lgeo = new THREE.BufferGeometry();
    lgeo.setAttribute('position', new THREE.BufferAttribute(lpos, 3));
    var lmat = new THREE.LineBasicMaterial({
      color: 0x3FB8AF, transparent: true, opacity: 0.08,
      depthWrite: false, blending: THREE.AdditiveBlending
    });
    scene.add(new THREE.LineSegments(lgeo, lmat));

    function rebuildLinks() {
      var n = 0;
      for (var a = 0; a < COUNT && n < MAX_L; a += 7) {
        for (var b = a+7; b < COUNT && n < MAX_L; b += 11) {
          var dx=pos[a*3]-pos[b*3], dy=pos[a*3+1]-pos[b*3+1], dz=pos[a*3+2]-pos[b*3+2];
          if (dx*dx+dy*dy+dz*dz < 5000) {
            lpos[n*6]=pos[a*3]; lpos[n*6+1]=pos[a*3+1]; lpos[n*6+2]=pos[a*3+2];
            lpos[n*6+3]=pos[b*3]; lpos[n*6+4]=pos[b*3+1]; lpos[n*6+5]=pos[b*3+2];
            n++;
          }
        }
      }
      for (var k=n*6; k<MAX_L*6; k++) lpos[k]=0;
      lgeo.attributes.position.needsUpdate = true;
    }
    rebuildLinks();

    // Mouse parallax
    var mx = 0, my = 0;
    doc.addEventListener('mousemove', function(e) {
      mx = (e.clientX / win.innerWidth)  - 0.5;
      my = (e.clientY / win.innerHeight) - 0.5;
    });

    win.addEventListener('resize', function() {
      camera.aspect = win.innerWidth / win.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(win.innerWidth, win.innerHeight);
    });

    var paused = false;
    doc.addEventListener('visibilitychange', function() { paused = doc.hidden; });

    var t = 0, frame = 0;
    function animate() {
      win.requestAnimationFrame(animate);
      if (paused) return;
      t += 0.005; frame++;
      if (!reduceMotion) {
        for (var i = 0; i < COUNT; i++) {
          pos[i*3]   += spd[i] * 0.25;
          pos[i*3+1] += Math.sin(t * 1.8 + i * 0.3) * 0.04;
          if (pos[i*3] > 450) pos[i*3] = -450;
        }
        geo.attributes.position.needsUpdate = true;
        if (frame % 80 === 0) rebuildLinks();
      }
      camera.position.x += (mx * 35 - camera.position.x) * 0.04;
      camera.position.y += (-my * 20 - camera.position.y) * 0.04;
      camera.lookAt(scene.position);
      renderer.render(scene, camera);
    }
    animate();
  }
})();
</script>
</body>
</html>
"""

# Embed CSS inline (avoids any escaping issues with external template vars)
_BOOTSTRAP = _HTML.replace('`CSS_PLACEHOLDER`', _CSS_FOR_PARENT.replace('`', r'\`'))


def render_3d_background() -> None:
    """
    Inject the 3D particle background. Call at the end of app.py.
    Uses st.html(unsafe_allow_javascript=True) -- the correct modern
    API in Streamlit 1.42+. components.v1.html was removed in 2026.
    """
    st.html(_BOOTSTRAP, unsafe_allow_javascript=True)
