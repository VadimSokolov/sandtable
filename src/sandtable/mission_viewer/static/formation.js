'use strict';
const FormationPreview = (() => {
  let data = null, review = null, map = null, mode = 'org', selected = 0, version = 0, timer = null, zoom = 1;

  const el = id => document.getElementById(id),
        e = s => String(s).replace(/[&<>"']/g, c => (({
          '&': '&amp;',
          '<': '&lt;',
          '>': '&gt;',
          '"': '&quot;',
          '\'': '&#39;'
        })[c])),
        f = n => Number(n).toLocaleString('en-US', {
          maximumFractionDigits: 2
        });

  const roles = ['Control', 'Cargo', 'Escort', 'Recovery'];

  function update(m, validated, mapInput) {
    const v = ++version;
    clearTimeout(timer);
    review = validated;
    map = mapInput;
    data = null;
    el('formationStatus').textContent = 'Updating Python layout…';
    el('formationDiagram').replaceChildren();
    el('formationCard').replaceChildren();

    timer = setTimeout(async () => {
      try {
        if (validated)
          data = validated.summary.formation;
        else {
          const r = await fetch('/api/formation', {
            method: 'POST',

            headers: {
              'Content-Type': 'application/json'
            },

            body: JSON.stringify({
              mission: m
            })
          });

          const x = await r.json();

          if (!r.ok)
            throw Error(x.error);

          if (v !== version)
            return;

          data = x;
        }

        if (v !== version)
          return;

        selected = Math.min(selected, data.vehicles.length - 1);
        render();
      } catch (err) {
        if (v === version) {
          data = null;
          el('formationStatus').textContent = 'Preview unavailable: ' + err.message;
          el('formationDiagram').replaceChildren();
        }
      }
    }, 180);
  }

  function vehicleButton(v) {
    return `<button class="vehicle-tile role-${v.role} ${v.id === selected ? 'selected' : ''}" data-vehicle="${v.id}" aria-pressed="${v.id === selected}" aria-label="${v.label}, ${roles[v.role]}, unit ${v.unit + 1}, serial ${v.serial + 1}"><span class="truck-glyph">▰</span><b>${v.label}</b><small>${roles[v.role]}</small><small>${v.crew} people${v.cargo_kg ? ' · ' + f(v.cargo_kg / 1000) + ' t' : ''}</small></button>`;
  }

  function render() {
    if (!data)
      return;

    el('orgView').setAttribute('aria-pressed', String(mode === 'org'));
    el('roadView').setAttribute('aria-pressed', String(mode === 'road'));
    el('formationStatus').textContent = (review ? 'VALIDATED INITIAL PLACEMENT' : 'CONFIGURATION PREVIEW · not map-validated') + ` · ${data.vehicles.length} vehicles · ${f(data.loaded_kg)} kg · ${data.crew} people · centre gap ${f(data.gap_m)} m`;
    let html = '';

    if (mode === 'org') {
      html = '<p class="formation-hint">Column → serial → march unit. Front is on the left. Tiles are symbols, not vehicle dimensions.</p>';

      for (let s = 0; s < data.serials; s++) {
        html += `<section class="serial-group"><h3>Serial ${s + 1}</h3>`;
        const units = [...new Set(data.vehicles.filter(v => v.serial === s).map(v => v.unit))];

        for (const u of units) {
          html += `<div class="unit-group"><b>March unit ${u + 1}</b><div class="unit-vehicles">${data.vehicles.filter(v => v.unit === u).map(vehicleButton).join('')}</div></div>`;
        }

        html += '</section>';
      }
    } else
      html = `<p class="formation-hint">${review ? 'Validated starting area, fitted to the convoy. The rest of the route is cropped; the full map is below. Vehicle symbols are enlarged for readability.' : 'Straight-road station illustration. Arrows indicate travel to the left. Map validation is still required.'} Centre span ${f(data.centre_span_m)} m; physical end-to-end span ${f(data.physical_span_m)} m.</p><div class="buttons"><button id="formationMinus" aria-label="Zoom formation out">−</button><button id="formationPlus" aria-label="Zoom formation in">+</button><button id="formationFit">Fit convoy</button><span>${f(zoom)}×</span></div><div class="formation-scroll">${svg()}</div>`;

    el('formationDiagram').innerHTML = html;

    el('formationDiagram').querySelectorAll('[data-vehicle]').forEach(b => {
      b.onclick = () => {
        selected = Number(b.dataset.vehicle);
        render();
      };

      b.onkeydown = k => {
        if (k.key === 'Enter' || k.key === ' ') {
          k.preventDefault();
          selected = Number(b.dataset.vehicle);
          render();
        }
      };
    });

    if (mode === 'road') {
      el('formationMinus').onclick = () => {
        zoom = Math.max(1, zoom / 1.5);
        render();
      };

      el('formationPlus').onclick = () => {
        zoom = Math.min(8, zoom * 1.5);
        render();
      };

      el('formationFit').onclick = () => {
        zoom = 1;
        render();
      };
    }

    card();
  }

  function svg() {
    const W = 1000, H = review ? 480 : 250, vs = data.vehicles, span = Math.max(data.centre_span_m, 1);
    let points;
    const sp = review?.summary.spawn;

    const bounds = sp ? [
      Math.min(...sp.map(p => p[0])) - 150,
      Math.min(...sp.map(p => p[1])) - 150,
      Math.max(...sp.map(p => p[0])) + 150,
      Math.max(...sp.map(p => p[1])) + 150
    ] : null;

    const mapScale = bounds ? Math.min(920 / (bounds[2] - bounds[0]), 400 / (bounds[3] - bounds[1])) : 1;

    if (review) {
      points = review.summary.spawn.map(p => [40 + (p[0] - bounds[0]) * mapScale, H - 40 - (p[1] - bounds[1]) * mapScale]);
    } else
      points = vs.map(v => [60 + 880 * (data.staging_m - v.station_m) / span, 110]);

    let out = `<svg role="img" aria-label="${review ? 'Validated convoy positions on the map' : 'Convoy station spacing'}" viewBox="0 0 ${W} ${H}" style="width:${100 * zoom}%;min-width:100%;height:auto"><defs><marker id="previewArrow" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="#556c7a"/></marker></defs>`;

    if (review) {
      const sc = mapScale, p = a => [40 + (a[0] - bounds[0]) * sc, H - 40 - (a[1] - bounds[1]) * sc];

      for (const b of map.buildings) {
        const q = p([b.box[0], b.box[3]]);
        out += `<rect x="${q[0]}" y="${q[1]}" width="${(b.box[2] - b.box[0]) * sc}" height="${(b.box[3] - b.box[1]) * sc}" fill="#d4dde0"/>`;
      }

      out += `<polyline points="${review.summary.route.map(x => p(x).join(',')).join(' ')}" fill="none" stroke="#40988e" stroke-width="4"/>`;
      const g = p(map.goal);
      out += `<circle cx="${g[0]}" cy="${g[1]}" r="8" fill="none" stroke="#07827b"/><text x="${g[0] - 22}" y="${g[1] - 15}">Goal</text>`;
    } else {
      for (const u of [...new Set(vs.map(v => v.unit))]) {
        const members = vs.filter(v => v.unit === u), a = points[members[0].id][0], b = points[members.at(-1).id][0];
        out += `<rect x="${a - 18}" y="75" width="${b - a + 36}" height="65" rx="6" fill="${u % 2 ? '#eaf1f7' : '#e8f4ef'}" stroke="#b4c8cb"/><text x="${(a + b) / 2}" y="63" font-size="${Math.max(8, Math.min(13, 800 / vs.length))}" text-anchor="middle">S${members[0].serial + 1} · Unit ${u + 1}</text>`;
      }

      out += '<path d="M960 110 H35" stroke="#dce6e9" stroke-width="35"/><text x="35" y="35">← Direction of travel · front / highest station</text>';

      for (let i = 1; i < vs.length; i++) {
        const a = points[i - 1], b = points[i];
        out += `<path d="M${a[0]} 170 H${b[0]}" stroke="#8399a1"/><text x="${(a[0] + b[0]) / 2}" y="190" text-anchor="middle" font-size="${Math.max(7, Math.min(12, 800 / vs.length))}">${f(data.gap_m)} m</text>`;
      }
    }

    if (el('formationLinks').checked) {
      const v = vs[selected], a = points[selected];

      for (const [target, color, offset] of [
        [v.head, '#556c7a', -22],
        [v.console === null ? null : vs.find(q => q.unit === v.console && q.id === q.head)?.id, '#8a5aa8', 22]
      ]) {
        if (target === null || target === undefined || target === selected)
          continue;

        const b = points[target];
        out += `<path d="M${a[0]} ${a[1] + offset} Q${(a[0] + b[0]) / 2} ${a[1] + offset * 3} ${b[0]} ${b[1] + offset}" stroke="${color}" fill="none" stroke-dasharray="5 3" marker-end="url(#previewArrow)"/>`;
      }
    }

    const colors = ['#1a6479', '#ca9541', '#ab5968', '#6977a6'];

    for (const v of vs) {
      const p = points[v.id], w = review ? 14 : Math.min(44, 700 / vs.length);
      out += `<g data-vehicle="${v.id}" tabindex="0" role="button" aria-label="${v.label} ${roles[v.role]}" style="cursor:pointer"><title>${v.label} · ${roles[v.role]} · unit ${v.unit + 1} · ${f(v.cargo_kg)} kg · ${v.crew} people</title><rect x="${p[0] - w / 2}" y="${p[1] - 10}" width="${w}" height="20" rx="3" fill="${colors[v.role]}" stroke="${selected === v.id ? '#142f3a' : 'white'}" stroke-width="${selected === v.id ? 3 : 1}"/><text x="${p[0]}" y="${p[1] - 17}" font-size="${review ? 10 : Math.min(13, 800 / vs.length)}" text-anchor="middle">${v.label}</text></g>`;
    }

    return out + '</svg>';
  }

  function card() {
    const v = data.vehicles[selected], host = data.vehicles.find(q => q.unit === v.console && q.id === q.head);
    el('formationCard').innerHTML = `<h3>${v.label} · ${roles[v.role]}</h3><div class="review-list"><span>Membership</span><b>Unit ${v.unit + 1} · Serial ${v.serial + 1}</b><span>Onboard people</span><b>${v.crew}</b><span>Cargo / capacity</span><b>${f(v.cargo_kg)} / ${f(v.capacity_kg)} kg${v.role !== 1 ? ' · not a cargo truck' : ''}</b><span>Unit head</span><b>V${v.head + 1}${v.id === v.head ? ' · this vehicle' : ''}</b><span>Console requests</span><b>${v.console === null ? 'Exempt · crewed or host' : `Console ${v.console + 1} · hosted by ${host.label}`}</b><span>Initial route station</span><b>${f(v.station_m)} m</b></div>${el('formationLinks').checked ? '<p>Solid membership is shown by unit groups. Dashed grey: selected vehicle → unit head. Dashed purple: selected vehicle → assigned console host. These are organizational assignments, not radio propagation or dynamic tracking targets.</p>' : ''}${!review ? data.warnings.map(w => '<p class="formation-hint">' + e(w) + '</p>').join('') : '<p>Positions correspond to the validated draft, not a replay or prediction of contact behavior.</p>'}`;
  }

  el('orgView').onclick = () => {
    mode = 'org';
    render();
  };

  el('roadView').onclick = () => {
    mode = 'road';
    render();
  };

  el('formationLinks').onchange = render;

  return {
    update
  };
})();
