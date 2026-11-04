'use strict';
function dirty() {
  RoadGraph.render(null);
  validated = null;
  comparisonCheck = null;
  $('run').disabled = true;
  $('runComparison').disabled = true;
  $('comparisonReview').replaceChildren();
  $('comparisonResults').hidden = true;
  $('draftStatus').textContent = 'Unvalidated draft';
  $('draftHint').textContent = 'Inputs changed. Validate and review before generating a new Python run.';
  $('review').replaceChildren();
  store();
  renderFleet();
  draw();
  scheduleExposure();
}

function readValue(field) {
  const key = field[0];

  if (key === 'cell')
    return draft.map.cell;

  if (key === 'red_range')
    return draft.map.red[0]?.weapon_range ?? 1000;

  return draft.mission[key];
}

function fieldHTML(f) {
  const [key, title, type, a, b, step, hint] = f, id = 'f_' + key, v = readValue(f);

  if (type === 'checkbox')
    return `<div class="field"><label class="check"><input id="${id}" data-field="${key}" type="checkbox" ${v ? 'checked' : ''}>${esc(title)}</label></div>`;

  if (type === 'select') return `<div class="field"><label for="${id}">${esc(title)}</label><select id="${id}" data-field="${key}">${a.map(
  ([val, t]) => `<option value="${esc(val)}" ${String(v) === String(val) ? 'selected' : ''}>${esc(t)}</option>`
).join('')}</select></div>`;

  return `<div class="field"><label for="${id}">${esc(title)}</label><input id="${id}" data-field="${key}" type="number" min="${a}" max="${b}" step="${step}" value="${v === null ? '' : v}">${hint ? `<small>${esc(hint)}</small>` : ''}</div>`;
}

function forms() {
  for (const [id, list] of [['basicFields', fields], ['advancedFields', advanced]]) {
    $(id).innerHTML = list.map(fieldHTML).join('');

    $(id).querySelectorAll('[data-field]').forEach(el => el.onchange = () => {
      checkpoint();
      const k = el.dataset.field;
      let v = el.type === 'checkbox' ? el.checked : el.tagName === 'SELECT' ? el.value : el.value === '' ? null : Number(el.value);

      if (k === 'comms')
        v = Number(v);

      if (k === 'cell')
        draft.map.cell = v;
      else if (k === 'red_range') {
        draft.map.red.forEach(r => r.weapon_range = v);
        redDefault = v;
      } else
        draft.mission[k] = v;

      dirty();
    });
  }

  syncMapFields();
}

function syncMapFields() {
  $('missionName').value = draft.name;
  $('worldWidth').value = draft.map.width;
  $('worldHeight').value = draft.map.height;
  $('goalRadius').value = draft.map.goal_radius;
  $('routeMode').value = draft.map.route_mode;
  $('routeAlgorithm').value = draft.map.route_algorithm || 'dijkstra';
  $('manualPath').value = draft.map.manual_path.join(', ');
  $('routeBias').value = draft.map.route_bias;
  $('biasValue').textContent = fmt(draft.map.route_bias);
  $('manualWrap').hidden = draft.map.route_mode !== 'manual';
}

function renderFleet() {
  FormationPreview.update(draft.mission, validated, draft.map);
  const m = draft.mission, U = (m.units_per_serial || 0) * (m.serials || 0), core = (m.vehicles_per_unit || 0) * U, N = core + (m.escorts || 0), cargo = Math.max(0, (m.vehicles_per_unit - 1 - (m.layout === 'recovery' ? 1 : 0)) * U), crew = U * m.control_crew + (m.escorts || 0) * m.escort_crew + (m.crew_mode === 'crewed' ? cargo * m.cargo_crew : 0) + (m.layout === 'recovery' ? U * m.recovery_crew : 0), load = cargo * (m.payload_kg || 0);

  $('fleetSummary').innerHTML = [
    ['Vehicles', N],
    ['Cargo trucks', cargo],
    ['Escorts', m.escorts],
    ['Onboard people', crew],
    ['Loaded cargo', fmt(load / 1000) + ' t']
  ].map(([k, v]) => `<div><small>${k}</small><b>${esc(v)}</b></div>`).join('');
}

async function validate() {
  notice('Validating graph, route, payload and initial placement…');
  $('validate').disabled = true;

  try {
    const c = await api('/api/validate', {
      config: draft
    });

    draft = c.config;
    validated = c;
    RoadGraph.render(c);
    forms();
    store();
    renderFleet();
    $('draftStatus').textContent = 'Validated · ready for review';
    $('draftHint').textContent = 'Run will use this exact configuration snapshot. No V2 recording is used.';
    $('run').disabled = false;
    const s = c.summary;

    $('review').innerHTML = `<div class="review-list">${[
  ['Vehicles', s.total_vehicles],
  ['Core + escorts', s.core_vehicles + ' + ' + s.escorts],
  ['Cargo trucks', s.cargo_trucks],
  ['People', s.crew],
  ['Loaded', fmt(s.loaded_kg) + ' kg'],
  ['Load / truck', fmt(s.effective_payload_kg) + ' kg'],
  ['Initial centre gap', fmt(s.initial_station_gap_m) + ' m'],
  ['Lead staging offset', fmt(draft.mission.staging_m) + ' m'],
  ['Initial formation span', fmt(s.staging_span_m) + ' m'],
  ['Route length', fmt(s.route_length_m) + ' m'],
  ['Route search', s.routing.algorithm],
  ['Weighted route cost', fmt(s.routing.cost)],
  ['Mean route exposure', fmt(s.routing.mean_exposure, 4)]
].map(([k, v]) => `<span>${esc(k)}</span><b>${esc(v)}</b>`).join('')}</div><p class="mono">Configuration ${esc(c.config_hash.slice(0, 16))}</p><ul class="warnings">${s.warnings.map(w => '<li>' + esc(w) + '</li>').join('')}</ul><details><summary>Selected route · edge exposure and Dijkstra/A* weights</summary><p>${esc(s.routing.formula)}. Known-map estimate, not a casualty probability. Both algorithms minimize the same cost.</p><div class="table-scroll"><table><thead><tr><th>Edge</th><th>Length (m)</th><th>Exposure</th><th>Weight / cost</th></tr></thead><tbody>${s.routing.selected_edges.map(
  e => `<tr><td>${esc(e.u)} → ${esc(e.v)}</td><td>${fmt(e.length_m)}</td><td>${fmt(e.exposure, 4)}</td><td>${fmt(e.cost)}</td></tr>`
).join('')}</tbody></table></div></details><details><summary>Full resolved configuration & definitions</summary><pre>${esc(JSON.stringify({
  config: draft,
  routing: s.routing,
  definitions: s.definitions
}, null, 2))}</pre></details>`;

    notice(
      `Valid: ${s.total_vehicles} vehicles, ${s.cargo_trucks} cargo trucks, ${s.crew} people, ${fmt(s.loaded_kg / 1000)} tonnes. Review the assumptions, then Run.`
    );

    draw();
  } catch (e) {
    validated = null;
    RoadGraph.render(null);
    $('run').disabled = true;
    notice(e.message, true);
    $('draftStatus').textContent = 'Validation failed';
  } finally {
    $('validate').disabled = false;
  }
}
