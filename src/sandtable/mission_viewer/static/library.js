'use strict';
const SavedScenarios = (() => {
  const $ = id => document.getElementById(id),
        esc = s => String(s).replace(/[&<>"']/g, c => (({
          '&': '&amp;',
          '<': '&lt;',
          '>': '&gt;',
          '"': '&quot;',
          '\'': '&#39;'
        })[c])),
        f = (n, d = 2) => n === null || n === undefined ? '—' : Number(n).toLocaleString('en-US', {
          maximumFractionDigits: d
        });

  let handlers,
      definition = null,
      jobs = [],
      job = null,
      result = {
        runs: []
      },
      selected = 'S1',
      seed = 0,
      timer = null,
      busy = false,
      wantedJob = null;

  const label = r => r === 'herringbone' ? 'Halt + Herringbone' : r === 'halt' ? 'Halt' : 'Continue';
  const interval = s => s?.ci95 ? s.ci95.map(x => f(x)).join(' to ') : 'Unavailable';

  async function api(url, body) {
    const r = await fetch(url, {
      method: body === undefined ? 'GET' : 'POST',

      headers: body === undefined ? {} : {
        'Content-Type': 'application/json'
      },

      body: body === undefined ? undefined : JSON.stringify(body)
    });

    const d = await r.json();

    if (!r.ok)
      throw Error(d.error || 'Request failed');

    return d;
  }

  const mean = (rows, key) => rows.length ? rows.reduce((s, r) => s + (r.outcome[key] || 0), 0) / rows.length : null;

  function scenario() {
    return definition?.scenarios.find(a => a.id === selected);
  }

  async function refresh() {
    if (!handlers || busy)
      return;

    busy = true;
    clearTimeout(timer);

    try {
      const d = await api('/api/library');
      definition = d.study;
      jobs = d.jobs;
      const preferred = jobs.find(j => ['queued', 'running'].includes(j.state)) || jobs.find(j => j.state === 'complete') || jobs[0];
      const id = wantedJob || job?.id || preferred?.id;
      wantedJob = null;
      job = id ? await api('/api/jobs/' + id) : null;

      result = job ? await api('/api/jobs/' + job.id + '/partial') : {
        runs: []
      };

      paint();
    } catch (e) {
      $('libraryMessage').textContent = 'Could not load saved study: ' + e.message;
    } finally {
      busy = false;

      if (wantedJob) {
        refresh();
        return;
      }

      if (job && ['queued', 'running'].includes(job.state))
        timer = setTimeout(refresh, 1500);
    }
  }

  function paint() {
    if (!definition)
      return;

    $('libraryJob').innerHTML = jobs.length ? jobs.map(
      j => `<option value="${j.id}" ${j.id === job?.id ? 'selected' : ''}>${esc(j.state)} · ${j.completed}/${j.total} · ${j.id.slice(0, 8)}</option>`
    ).join('') : '<option>No saved execution yet</option>';

    const active = job && ['queued', 'running'].includes(job.state);
    $('runLibrary').disabled = !!active;
    $('cancelLibrary').disabled = !active;
    $('libraryProgress').value = job?.completed || 0;
    $('libraryProgressText').textContent = job ? `${job.state.toUpperCase()} · ${job.completed}/${job.total} completed · ${job.message}${job.tick !== undefined ? ' · step ' + job.tick : ''}` : '12 saved configurations ready; no missions executed yet.';
    $('libraryMessage').textContent = job?.state === 'complete' ? 'All 240 Python missions are saved. Choose a scenario and seed to inspect.' : active ? 'Study running. Completed seeds can already be replayed; partial averages are provisional.' : job ? job.message : 'The input scenarios are saved. Starting the study creates 240 new Python runs; it does not use archived V2 recordings.';

    $('libraryScenario').innerHTML = definition.scenarios.map(
      a => `<option value="${a.id}" ${a.id === selected ? 'selected' : ''}>${a.id} · core ${a.factors.core} · ${label(a.factors.response)} · C${a.factors.comms}</option>`
    ).join('');

    detail();
    matrix();
    diagnostics();
    interactions();
    $('libraryScope').innerHTML = `<p>${esc(definition.design)}</p><ul>${definition.scope.map(s => '<li>' + esc(s) + '</li>').join('')}</ul><p>Capacity: 1 short ton = 907.18474 kg. Loaded payload: 900 kg with 12 cargo trucks, 600 kg with 18. Handoff 5 s, console transfer 20 s, span capacity 4, fixed staging offset 1,400 m, commanded pace 10 m/s, time gap 4 s, minimum gap 40 m, horizon 1,800 s, required delivery 100%.</p><p class="mono">Design SHA-256: ${esc(definition.design_hash)}${result.provenance ? '<br>Recorded source SHA-256: ' + esc(result.provenance.source_digest) : ''}</p><details><summary>Exact common baseline input</summary><pre>${esc(JSON.stringify(definition.scenarios[0].configuration, null, 2))}</pre></details>`;
    $('downloadLibraryResults').disabled = !result.runs?.length;
  }

  function detail() {
    const a = scenario();

    if (!a)
      return;

    const m = a.configuration.mission, rows = (result.runs || []).filter(r => r.arm === selected), row = rows.find(r => r.seed === seed);

    $('librarySeed').innerHTML = definition.seeds.map(
      s => `<option value="${s}" ${s === seed ? 'selected' : ''}>Seed ${s} · ${rows.some(r => r.seed === s) ? 'saved' : 'pending'}</option>`
    ).join('');

    $('replayLibrary').disabled = !row;
    $('replayLibrary').textContent = row ? `Watch ${selected} · seed ${seed}` : 'Replay pending';
    $('libraryScenarioDetail').innerHTML = `<div class="eyebrow">SAVED CONFIGURATION · ${selected}</div><h2>${label(m.response)} · C${m.comms} · ${m.vehicles_per_unit} core vehicles/unit</h2><div class="library-facts"><div><small>Total vehicles</small><b>${m.vehicles_per_unit * 3 + 3}</b></div><div><small>Cargo trucks</small><b>${(m.vehicles_per_unit - 1) * 3}</b></div><div><small>Payload / capacity</small><b>${f(m.payload_kg)} / ${f(m.capacity_kg, 5)} kg</b></div><div><small>Loaded cargo</small><b>10,800 kg</b></div><div><small>Onboard people</small><b>15</b></div><div><small>Saved seeds</small><b>${rows.length}/20</b></div></div><p>Promote after 5 steps → experimental crewed-successor console transfer after 20 s. Red control-first; natural combat. Same fixed lower-loop route.</p>${row ? `<p><b>Selected seed's final record:</b> ${f(row.outcome.cargo_delivered * 1000)} kg delivered · ${f(row.outcome.crew_lost)} crew lost · ${f(row.outcome.crew_steps_at_risk)} crew-steps. The replay itself starts at t=0.</p>` : '<p>This seed has no completed saved recording yet.</p>'}`;
  }

  function matrix() {
    const complete = job?.state === 'complete';
    $('libraryResultScope').textContent = complete ? 'Completed 20-seed means. Different metrics have different tradeoffs; no automatic overall ranking.' : 'Averages below include completed seeds only. Unequal sample counts are provisional and should not be ranked.';

    $('libraryMatrix').innerHTML = `<table><thead><tr><th>Scenario</th><th>Core/unit</th><th>Response</th><th>Comms</th><th>Vehicles</th><th>Load/truck kg</th><th>n/20</th><th>Delivered kg</th><th>Exposure crew-steps</th><th>Crew lost</th><th>Vehicle losses</th><th>Cargo success</th><th>Inspect</th></tr></thead><tbody>${definition.scenarios.map(a => {
  const rows = (result.runs || []).filter(r => r.arm === a.id), m = a.configuration.mission;
  return `<tr class="${selected === a.id ? 'library-selected' : ''}"><td><b>${a.id}</b></td><td>${a.factors.core}</td><td>${label(a.factors.response)}</td><td>C${a.factors.comms}</td><td>${a.factors.core * 3 + 3}</td><td>${f(m.payload_kg)}</td><td>${rows.length}</td><td>${rows.length ? f(mean(rows, 'cargo_delivered') * 1000) : '—'}</td><td>${f(mean(rows, 'crew_steps_at_risk'))}</td><td>${f(mean(rows, 'crew_lost'))}</td><td>${f(mean(rows, 'blue_losses'))}</td><td>${rows.length ? f(mean(rows, 'cargo_success') * 100) + '%' : '—'}</td><td><button data-scenario="${a.id}">Select ${a.id}</button></td></tr>`;
}).join('')}</tbody></table>`;

    $('libraryMatrix').querySelectorAll('[data-scenario]').forEach(b => b.onclick = () => {
      selected = b.dataset.scenario;
      paint();

      $('libraryScenarioDetail').scrollIntoView({
        block: 'center',
        behavior: 'smooth'
      });
    });
  }

  function diagnostics() {
    const stats = result.study_summary?.scenarios;

    if (!stats) {
      $('libraryDiagnostics').textContent = 'Full uncertainty and diagnostic summaries appear when all 240 missions finish.';
      return;
    }

    $('libraryDiagnostics').innerHTML = `<p>Mean 95% Student t intervals are descriptive and unadjusted. Shared seeds do not ensure identical paths after divergence. Zero-containing intervals are not evidence of equivalence. Head-loss and console-transfer columns verify which mechanisms actually occurred.</p><div class="table-scroll"><table><thead><tr><th>Scenario</th><th>Delivery mean / 95% CI (t)</th><th>Exposure mean / 95% CI</th><th>Contact runs</th><th>Head-loss runs</th><th>Mean handoffs</th><th>Mean console transfers</th><th>Mean accepted services</th><th>Mean run duration s</th><th>Full-delivery time s (successful runs only)</th></tr></thead><tbody>${stats.map(a => {
  const m = a.metrics, t = a.time_to_full_delivery;
  return `<tr><td>${a.arm}</td><td>${f(m.cargo_delivered.mean)} · ${interval(m.cargo_delivered)}</td><td>${f(m.crew_steps_at_risk.mean)} · ${interval(m.crew_steps_at_risk)}</td><td>${f(m.v3_contact_occurred.mean * m.v3_contact_occurred.n, 0)}/20</td><td>${f(m.v3_head_loss_occurred.mean * m.v3_head_loss_occurred.n, 0)}/20</td><td>${f(m.ll_handoffs.mean)}</td><td>${f(m.v3_console_transfers.mean)}</td><td>${f(m.v3_console_services.mean)}</td><td>${f(m.mission_time.mean)}</td><td>${f(t.mean)} · n=${t.n}</td></tr>`;
}).join('')}</tbody></table></div><p>Run duration includes failures and horizon-limited runs. Full-delivery time is conditional on success and is not directly comparable when success rates differ. Accepted services are not confirmed answer deliveries.</p>`;
  }

  function interactions() {
    const xs = result.study_summary?.interactions;

    if (!xs) {
      $('libraryInteractions').textContent = 'Paired interaction contrasts appear after completion.';
      return;
    }

    $('libraryInteractions').innerHTML = `<p>For each seed: (response − Continue under C3) − (response − Continue under C0). A nonzero value describes how the response effect changes with comms in this model. Intervals are exploratory, unadjusted; these contrasts are not policy rankings.</p><div class="table-scroll"><table><thead><tr><th>Core/unit</th><th>Response</th><th>Contrast</th><th>Metric</th><th>n</th><th>Mean interaction</th><th>Paired 95% t CI</th></tr></thead><tbody>${xs.flatMap(a => Object.entries(a.metrics).map(
  ([k, s]) => `<tr><td>${a.core}</td><td>${label(a.response)}</td><td>${esc(a.formula)}</td><td>${esc(k)}</td><td>${s.n}</td><td>${f(s.mean)}</td><td>${interval(s)}</td></tr>`
)).join('')}</tbody></table></div>`;
  }

  function init(h) {
    handlers = h;
    $('refreshLibrary').onclick = refresh;

    $('libraryScenario').onchange = () => {
      selected = $('libraryScenario').value;
      detail();
      matrix();
    };

    $('librarySeed').onchange = () => {
      seed = Number($('librarySeed').value);
      detail();
    };

    $('libraryJob').onchange = () => {
      wantedJob = $('libraryJob').value;
      refresh();
    };

    $('runLibrary').onclick = async () => {
      try {
        $('runLibrary').disabled = true;
        const r = await api('/api/library/run', {});
        wantedJob = r.id;
        await refresh();
      } catch (e) {
        $('runLibrary').disabled = false;
        handlers.error(e.message);
      }
    };

    $('cancelLibrary').onclick = async () => {
      if (job) {
        await api('/api/jobs/' + job.id + '/cancel', {});
        await refresh();
      }
    };

    $('loadLibraryConfig').onclick = () => handlers.loadConfig(scenario().configuration, 'config');
    $('previewLibraryMap').onclick = () => handlers.loadConfig(scenario().configuration, 'map');
    $('downloadLibraryConfig').onclick = () => handlers.download(selected + '-scenario.json', scenario().configuration);
    $('downloadLibraryDesign').onclick = () => handlers.download('sketch-12-study-design.json', definition);
    $('downloadLibraryResults').onclick = () => handlers.download('sketch-12-study-' + job.id.slice(0, 8) + '.json', result);

    $('replayLibrary').onclick = () => {
      const row = (result.runs || []).find(r => r.arm === selected && r.seed === seed);

      if (row)
        handlers.replay(job.id, row.index);
    };
  }

  function showJob(id) {
    wantedJob = id;
    refresh();
  }

  return {
    init,
    refresh,
    showJob
  };
})();
