"""
Trade Routes Globe — real country borders via D3 geoOrthographic.

Replaces the blank Three.js wireframe sphere with a proper interactive
world map rendered using:
  - D3.js geoOrthographic projection (real geographic sphere)
  - Natural Earth 110m country borders (world-atlas TopoJSON from jsdelivr)
  - TopoJSON client library for border extraction
  - Animated great-circle arcs from India to target markets
  - Score-colored pulsing markers with country name + score tooltips
  - Drag to rotate, scroll to zoom, click marker for details
"""

import json
import streamlit as _st_globe

_COUNTRY_COORDS = {
    "IN": (20.6, 78.9),
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
    "CN": (35.9, 104.2),
    "KR": (36.5, 127.5),
    "BR": (-14.2, -51.9),
    "ZA": (-30.6, 22.9),
    "SA": (23.9, 45.1),
}

_COUNTRY_NAMES = {
    "IN": "India", "US": "United States", "DE": "Germany",
    "GB": "United Kingdom", "CA": "Canada", "AU": "Australia",
    "AE": "UAE", "SG": "Singapore", "JP": "Japan",
    "FR": "France", "IT": "Italy", "ES": "Spain",
    "NL": "Netherlands", "BE": "Belgium", "CN": "China",
    "KR": "South Korea", "BR": "Brazil", "ZA": "South Africa",
    "SA": "Saudi Arabia",
}


def _score_color(score: float) -> str:
    if score >= 60:
        return "#3FB8AF"
    if score >= 30:
        return "#E3A857"
    return "#E2725B"


def render_trade_globe(opportunity_scores: list[dict], height: int = 500) -> None:
    best: dict[str, float] = {}
    for s in opportunity_scores or []:
        code = s.get("destination_country", "").upper()
        score = float(s.get("score", 0))
        if code in _COUNTRY_COORDS:
            best[code] = max(best.get(code, 0), score)

    if not best:
        return

    markets = [
        {
            "code": code,
            "name": _COUNTRY_NAMES.get(code, code),
            "lat": _COUNTRY_COORDS[code][0],
            "lon": _COUNTRY_COORDS[code][1],
            "score": round(score, 1),
            "color": _score_color(score),
        }
        for code, score in best.items()
    ]

    origin = {
        "lat": _COUNTRY_COORDS["IN"][0],
        "lon": _COUNTRY_COORDS["IN"][1],
        "name": "India (Origin)",
    }

    html = _build_html(markets, origin)
    # Wrap in a fixed-height div since st.html auto-sizes
    import urllib.parse
    # st.iframe (Streamlit 1.42+) is the correct replacement for
    # components.v1.iframe, which is removed after 2026-06-01.
    encoded = urllib.parse.quote(html, safe="")
    _st_globe.iframe(f"data:text/html,{encoded}", height=height)


def _build_html(markets, origin) -> str:
    markets_json = json.dumps(markets)
    origin_json = json.dumps(origin)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  html, body {{
    margin: 0; padding: 0;
    background: #0D1220;
    font-family: Arial, sans-serif;
    overflow: hidden;
  }}
  #globe-container {{
    position: relative;
    width: 100%;
    height: 100vh;
  }}
  svg {{
    width: 100%;
    height: 100%;
    cursor: grab;
  }}
  svg:active {{ cursor: grabbing; }}

  .country {{
    fill: #1a2540;
    stroke: #2d4070;
    stroke-width: 0.5px;
    transition: fill 0.2s;
  }}
  .country:hover {{ fill: #243560; }}
  .graticule {{
    fill: none;
    stroke: #1c2d50;
    stroke-width: 0.4px;
  }}
  .sphere {{
    fill: #0d1833;
  }}
  .border {{
    fill: none;
    stroke: #3a5080;
    stroke-width: 0.8px;
  }}
  .arc {{
    fill: none;
    stroke-width: 1.8px;
    opacity: 0;
    stroke-dasharray: 1000;
    stroke-dashoffset: 1000;
  }}
  .origin-marker {{
    fill: #E3A857;
    stroke: #fff;
    stroke-width: 1.5px;
  }}
  .origin-ring {{
    fill: none;
    stroke: #E3A857;
    stroke-width: 1.5px;
    opacity: 0.7;
  }}
  .dest-marker {{
    stroke: #fff;
    stroke-width: 1px;
    cursor: pointer;
  }}
  .dest-ring {{
    fill: none;
    stroke-width: 1px;
    opacity: 0.5;
  }}
  .india-label {{
    fill: #E3A857;
    font-size: 11px;
    font-weight: bold;
    pointer-events: none;
  }}
  .dest-label {{
    fill: #EDEAE2;
    font-size: 10px;
    font-weight: 600;
    pointer-events: none;
    text-shadow: 0 1px 3px #0d1220;
    paint-order: stroke;
    stroke: #0d1220;
    stroke-width: 3px;
  }}

  /* Tooltip */
  #tooltip {{
    position: absolute;
    background: rgba(22,29,51,0.95);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 10px;
    padding: 10px 14px;
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.2s;
    min-width: 150px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.5);
  }}
  #tooltip .tt-country {{ color: #EDEAE2; font-size: 13px; font-weight: bold; margin-bottom: 4px; }}
  #tooltip .tt-score {{ font-size: 22px; font-weight: bold; font-family: Georgia, serif; }}
  #tooltip .tt-label {{ color: #9CA3BF; font-size: 10px; margin-top: 2px; }}
  #tooltip .tt-strong {{ color: #3FB8AF; }}
  #tooltip .tt-mod {{ color: #E3A857; }}
  #tooltip .tt-weak {{ color: #E2725B; }}

  /* Legend */
  #legend {{
    position: absolute;
    bottom: 12px;
    left: 12px;
    background: rgba(13,18,32,0.8);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 11px;
    color: #9CA3BF;
  }}
  #legend .row {{ display: flex; align-items: center; gap: 6px; margin: 3px 0; }}
  #legend .dot {{ width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }}
  #hint {{
    position: absolute;
    top: 10px;
    right: 12px;
    font-size: 10.5px;
    color: #9CA3BF;
    background: rgba(13,18,32,0.7);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 6px;
    padding: 4px 9px;
  }}
  #fallback {{
    display: none;
    color: #9CA3BF;
    font-size: 13px;
    padding: 40px;
    text-align: center;
  }}
</style>
</head>
<body>
<div id="globe-container">
  <svg id="globe-svg"></svg>
  <div id="tooltip"><div class="tt-country"></div><div class="tt-score"></div><div class="tt-label"></div></div>
  <div id="legend">
    <div class="row"><div class="dot" style="background:#3FB8AF"></div> Strong (60+)</div>
    <div class="row"><div class="dot" style="background:#E3A857"></div> Moderate (30–60)</div>
    <div class="row"><div class="dot" style="background:#E2725B"></div> Weak (&lt;30)</div>
    <div class="row"><div class="dot" style="background:#E3A857;border:2px solid #fff"></div> India (origin)</div>
  </div>
  <div id="hint">Drag · Scroll · Hover</div>
  <div id="fallback">Globe unavailable — check internet connection</div>
</div>

<!-- D3 -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<!-- TopoJSON client -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/topojson/3.0.2/topojson.min.js"></script>

<script>
var MARKETS = {markets_json};
var ORIGIN  = {origin_json};

window.addEventListener('load', function() {{
  if (typeof d3 === 'undefined' || typeof topojson === 'undefined') {{
    document.getElementById('fallback').style.display = 'block';
    document.getElementById('globe-svg').style.display = 'none';
    return;
  }}
  buildGlobe();
}});

function buildGlobe() {{
  var container = document.getElementById('globe-container');
  var W = container.clientWidth  || 700;
  var H = container.clientHeight || 480;
  var RADIUS = Math.min(W, H) * 0.44;

  // Projection: start centered on India
  var projection = d3.geoOrthographic()
    .scale(RADIUS)
    .translate([W / 2, H / 2])
    .clipAngle(90)
    .rotate([-78.9, -20.6, 0]);   // [lon, lat] negated for rotate

  var path = d3.geoPath().projection(projection);
  var graticule = d3.geoGraticule()();

  var svg = d3.select('#globe-svg')
    .attr('viewBox', '0 0 ' + W + ' ' + H);

  // Sphere (ocean)
  svg.append('path')
    .datum({{type:'Sphere'}})
    .attr('class','sphere')
    .attr('d', path);

  // Graticule (grid lines)
  svg.append('path')
    .datum(graticule)
    .attr('class','graticule')
    .attr('d', path);

  // Country fills + borders from Natural Earth TopoJSON
  fetch('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json')
    .then(function(r) {{ return r.json(); }})
    .then(function(world) {{
      var countries = topojson.feature(world, world.objects.countries);
      var borders   = topojson.mesh(world, world.objects.countries,
                        function(a,b) {{ return a !== b; }});

      svg.insert('g', '.graticule + *')
        .selectAll('path')
        .data(countries.features)
        .join('path')
        .attr('class', 'country')
        .attr('d', path);

      svg.append('path')
        .datum(borders)
        .attr('class','border')
        .attr('d', path);

      // Re-render on rotation
      function redraw() {{
        svg.selectAll('.sphere,.graticule,.country,.border')
           .each(function(d) {{ d3.select(this).attr('d', path(d || this.__data__)); }});
        svg.selectAll('.sphere').attr('d', path({{type:'Sphere'}}));
        svg.selectAll('.graticule').attr('d', path(graticule));
        svg.selectAll('.country').attr('d', path);
        svg.selectAll('.border').attr('d', path);
        updateMarkers();
        updateArcs();
      }}

      addInteraction(projection, redraw, W, H);
      addMarkersAndArcs(svg, projection, path, redraw);
    }})
    .catch(function() {{
      // Countries failed to load -- still show sphere + markers
      addInteraction(projection, function() {{
        svg.selectAll('.sphere').attr('d', path({{type:'Sphere'}}));
        svg.selectAll('.graticule').attr('d', path(graticule));
        updateMarkers();
        updateArcs();
      }}, W, H);
      addMarkersAndArcs(svg, projection, path, function() {{}});
    }});

  var _updateMarkers, _updateArcs;

  function updateMarkers() {{ if (_updateMarkers) _updateMarkers(); }}
  function updateArcs()    {{ if (_updateArcs)    _updateArcs();    }}

  function addMarkersAndArcs(svg, projection, path, redraw) {{

    // --- Arcs (great circles) ---
    var arcGroup = svg.append('g').attr('class','arc-group');

    MARKETS.forEach(function(m, i) {{
      var arcData = {{
        type: 'Feature',
        geometry: {{
          type: 'LineString',
          coordinates: [
            [ORIGIN.lon, ORIGIN.lat],
            [m.lon, m.lat]
          ]
        }}
      }};

      var arcEl = arcGroup.append('path')
        .datum(arcData)
        .attr('class', 'arc')
        .attr('id', 'arc-' + m.code)
        .attr('stroke', m.color)
        .attr('d', path);

      // Animate arc drawing with a stagger
      setTimeout(function() {{
        var totalLen = arcEl.node().getTotalLength() || 800;
        arcEl
          .attr('stroke-dasharray', totalLen + ' ' + totalLen)
          .attr('stroke-dashoffset', totalLen)
          .style('opacity', 0.75)
          .transition()
          .duration(1400)
          .ease(d3.easeCubicInOut)
          .attr('stroke-dashoffset', 0);
      }}, 300 + i * 180);
    }});

    _updateArcs = function() {{
      arcGroup.selectAll('path').each(function(d) {{
        d3.select(this).attr('d', path(d));
      }});
    }};

    // --- Destination markers ---
    var markerGroup = svg.append('g').attr('class','marker-group');
    var tooltip = document.getElementById('tooltip');

    // Origin marker (India)
    var originEl = markerGroup.append('g').attr('class','origin-g');
    originEl.append('circle').attr('class','origin-ring').attr('r', 12).attr('stroke','#E3A857');
    originEl.append('circle').attr('class','origin-marker').attr('r', 6);

    // Pulsing ring animation on origin
    function pulseOrigin() {{
      originEl.select('.origin-ring')
        .attr('r', 6).style('opacity', 0.8)
        .transition().duration(1600)
        .attr('r', 18).style('opacity', 0)
        .on('end', pulseOrigin);
    }}
    pulseOrigin();

    // Destination markers
    var destGs = markerGroup.selectAll('.dest-g')
      .data(MARKETS)
      .join('g')
      .attr('class','dest-g')
      .style('cursor','pointer');

    destGs.append('circle')
      .attr('class','dest-ring')
      .attr('r', function(d) {{ return 5 + (d.score / 100) * 8; }})
      .attr('stroke', function(d) {{ return d.color; }});

    destGs.append('circle')
      .attr('class','dest-marker')
      .attr('r', function(d) {{ return 4 + (d.score / 100) * 5; }})
      .attr('fill', function(d) {{ return d.color; }});

    destGs.append('text')
      .attr('class','dest-label')
      .attr('dy', function(d) {{ return -(6 + (d.score / 100) * 5 + 5); }})
      .attr('text-anchor','middle')
      .text(function(d) {{ return d.name; }});

    // Tooltip
    destGs
      .on('mouseover', function(event, d) {{
        var lvl = d.score >= 60 ? 'Strong opportunity' : d.score >= 30 ? 'Moderate opportunity' : 'Weak opportunity';
        var cls = d.score >= 60 ? 'tt-strong' : d.score >= 30 ? 'tt-mod' : 'tt-weak';
        tooltip.querySelector('.tt-country').textContent = d.name;
        tooltip.querySelector('.tt-score').textContent = d.score + ' / 100';
        tooltip.querySelector('.tt-score').className = 'tt-score ' + cls;
        tooltip.querySelector('.tt-label').textContent = lvl;
        tooltip.style.opacity = '1';
      }})
      .on('mousemove', function(event) {{
        var x = event.pageX + 14, y = event.pageY - 10;
        tooltip.style.left = x + 'px';
        tooltip.style.top  = y + 'px';
      }})
      .on('mouseout', function() {{
        tooltip.style.opacity = '0';
      }});

    function placeMarkers() {{
      // Origin
      var op = projection([ORIGIN.lon, ORIGIN.lat]);
      var vis = op !== null;
      originEl.attr('transform', vis ? 'translate(' + op[0] + ',' + op[1] + ')' : 'translate(-9999,-9999)');

      // India label
      svg.selectAll('.india-label').remove();
      if (vis) {{
        svg.append('text').attr('class','india-label')
          .attr('x', op[0]).attr('y', op[1] - 14)
          .attr('text-anchor','middle')
          .text('India');
      }}

      // Destinations
      destGs.each(function(d) {{
        var p = projection([d.lon, d.lat]);
        var v = p !== null;
        d3.select(this).attr('transform', v ? 'translate(' + p[0] + ',' + p[1] + ')' : 'translate(-9999,-9999)');
      }});
    }}

    _updateMarkers = placeMarkers;
    placeMarkers();
  }}

  function addInteraction(projection, redraw, W, H) {{
    var drag = d3.drag()
      .on('start', function() {{ d3.select('svg').style('cursor','grabbing'); }})
      .on('drag', function(event) {{
        var rot = projection.rotate();
        var k = 75 / projection.scale();
        projection.rotate([rot[0] + event.dx * k, rot[1] - event.dy * k, rot[2]]);
        redraw();
      }})
      .on('end', function() {{ d3.select('svg').style('cursor','grab'); }});

    var zoom = d3.zoom()
      .scaleExtent([0.5, 4])
      .on('zoom', function(event) {{
        var scale = RADIUS * event.transform.k;
        projection.scale(scale);
        redraw();
      }});

    d3.select('svg').call(drag).call(zoom);
    window.addEventListener('resize', function() {{
      var W2 = container.clientWidth, H2 = container.clientHeight;
      svg.attr('viewBox', '0 0 ' + W2 + ' ' + H2);
      projection.translate([W2/2, H2/2]);
      redraw();
    }});
  }}
}}
</script>
</body>
</html>"""


