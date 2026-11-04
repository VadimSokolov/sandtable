'use strict';
const RoadGraph = (() => {
  let input = null, selected = null, zoom = 1;

  const root = () => document.getElementById('roadGraphPanel'),
        f = n => Number(n).toLocaleString('en-US', {
          maximumFractionDigits: 4
        }),
        esc = s => String(s).replace(/[&<>"']/g, c => (({
          '&': '&amp;',
          '<': '&lt;',
          '>': '&gt;',
          '"': '&quot;',
          '\'': '&#39;'
        })[c]));

  function render(c) {
    input = c;

    if (!c) {
      root().hidden = true;
      root().replaceChildren();
      return;
    }

    selected = null;
    zoom = 1;
    paint();
  }

  function paint() {
    const s = input.summary, r = s.routing, edges = r.all_edges, ns = new Map(s.graph.nodes.map(n => [n.id, n]));
    root().hidden = document.getElementById('mapTab').getAttribute('aria-selected') !== 'true';

    const W = 1000,
          H = 500,
          scale = Math.min(860 / input.config.map.width, 360 / input.config.map.height),
          p = k => {
            const n = ns.get(k);
            return [70 + n.x * scale, H - 70 - n.y * scale];
          };

    let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Road graph with every edge cost and selected path" style="width:${zoom * 100}%;min-width:100%;height:auto">`;

    for (const e of edges) {
      const a = p(e.u), b = p(e.v), x = (a[0] + b[0]) / 2, y = (a[1] + b[1]) / 2;
      svg += `<g><line x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}" stroke="${e.id === selected ? '#cf9235' : e.selected ? '#087e70' : '#a8b8c2'}" stroke-width="${e.selected ? 5 : 2}"/><rect x="${x - 50}" y="${y - 19}" width="100" height="22" rx="4" fill="white" opacity=".94"/><text x="${x}" y="${y - 4}" font-size="12" text-anchor="middle">${e.id} · ${f(e.cost)}</text></g>`;
    }

    for (const n of s.graph.nodes) {
      const a = p(n.id);
      svg += `<circle cx="${a[0]}" cy="${a[1]}" r="6" fill="#183847"/><text x="${a[0] + 9}" y="${a[1] - 10}" font-size="12">${esc(n.id)}</text>`;
    }

    svg += '</svg>';
    let cumulative = 0;

    const steps = r.selected_edges.map((e, i) => {
      cumulative += e.cost;
      return `<tr><td>${i + 1}</td><td>${esc(e.u)} → ${esc(e.v)}</td><td>${f(e.cost)}</td><td>${f(cumulative)}</td></tr>`;
    }).join('');

    root().innerHTML = `<div class="eyebrow">VALIDATED ROAD GRAPH · INITIAL PLANNING</div><h2>See how the path cost is built.</h2><p>Green edges form the chosen path. Labels are <b>edge ID · cost</b>. Every original road is split at connected crossings and projected markers; the table lists the resulting graph edges.</p><p><b>${esc(r.algorithm.toUpperCase())}</b> · ${s.route_nodes.map(esc).join(' → ')}<br>Path length: <b>${f(s.route_length_m)} m</b> · Total path cost: <b>${f(r.cost)}</b></p><div class="buttons"><button id="graphOut">−</button><button id="graphIn">+</button><button id="graphFit">Fit graph</button><span>${f(zoom)}× · scroll to pan when zoomed</span></div><div class="formation-scroll">${svg}</div><p><code>w = L / s × (1 + 10 × b × E)</code><br>L: segment length (m), s: trafficability, b: exposure penalty weight = <b>${f(r.penalty_weight)}</b>, E: used exposure score. Cost is effective metres, not seconds or a casualty probability. Automatic exposure is the sampled known-map estimate; manual overrides remain labelled.</p><div id="edgeCalculation" class="model-note">Select “Explain” beside any edge to see its numeric calculation.</div><h3>Every graph edge</h3><div class="table-scroll"><table><thead><tr><th>Edge / source road</th><th>Nodes</th><th>L (m)</th><th>s</th><th>E / source</th><th>Cost</th><th>Chosen?</th><th>Calculation</th></tr></thead><tbody>${edges.map(
  e => `<tr class="${e.selected ? 'graph-chosen' : ''}"><td>${e.id} / ${esc(e.road_id)}</td><td>${esc(e.u)} ↔ ${esc(e.v)}</td><td>${f(e.length_m)}</td><td>${f(e.speed_mult)}</td><td>${f(e.exposure)} · ${esc(e.exposure_mode)}</td><td><b>${f(e.cost)}</b></td><td>${e.selected ? 'Yes' : '—'}</td><td><button data-explain="${e.id}" aria-label="Explain edge ${e.id}">Explain</button></td></tr>`
).join('')}</tbody></table></div><h3>Chosen path · cumulative cost</h3><div class="table-scroll"><table><thead><tr><th>Step</th><th>Traversal</th><th>Edge cost</th><th>Running total</th></tr></thead><tbody>${steps}</tbody></table></div><p><b>Total = ${r.selected_edges.map(e => f(e.cost)).join(' + ')} = ${f(r.cost)}</b>. Displayed numbers are rounded; totals use full precision.</p><p class="formation-hint">This graph describes the validated draft. Editing the map or mission clears it until revalidation. Dijkstra and A* optimize the same objective; a manual path is evaluated without an optimality claim.</p>`;

    document.getElementById('graphOut').onclick = () => {
      zoom = Math.max(1, zoom / 1.5);
      paint();
    };

    document.getElementById('graphIn').onclick = () => {
      zoom = Math.min(8, zoom * 1.5);
      paint();
    };

    document.getElementById('graphFit').onclick = () => {
      zoom = 1;
      paint();
    };

    root().querySelectorAll('[data-explain]').forEach(b => b.onclick = () => {
      selected = b.dataset.explain;
      explain();

      document.getElementById('edgeCalculation').scrollIntoView({
        block: 'center',
        behavior: 'smooth'
      });
    });

    if (selected)
      explain();
  }

  function explain() {
    const e = input.summary.routing.all_edges.find(e => e.id === selected), b = input.summary.routing.penalty_weight;
    document.getElementById('edgeCalculation').innerHTML = `<h3>${e.id} · road ${esc(e.road_id)} · ${esc(e.u)} ↔ ${esc(e.v)}</h3><p>1. Baseline = L / s = ${f(e.length_m)} / ${f(e.speed_mult)} = <b>${f(e.baseline_cost)}</b></p><p>2. Penalty multiplier = 1 + 10 × ${f(b)} × ${f(e.exposure)} = <b>${f(e.penalty_multiplier)}</b></p><p>3. Edge cost = ${f(e.baseline_cost)} × ${f(e.penalty_multiplier)} = <b>${f(e.cost)}</b></p><p>Values displayed above are rounded; the calculation uses full precision. Exposure source: ${esc(e.exposure_mode)}. ${e.selected ? 'This edge contributes to the chosen path.' : 'This edge is not on the chosen path.'}</p>`;
  }

  return {
    render
  };
})();
