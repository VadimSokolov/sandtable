'use strict';
function reviewDesign() {
  const parameter = $('factor').value, text = $('values').value.trim(), stringFactors = ['response', 'leader_loss'];
  const values = text.split(',').map(x => x.trim()).filter(Boolean).map(x => stringFactors.includes(parameter) ? x : Number(x));

  if (values.some(x => typeof x === 'number' && !Number.isFinite(x)))
    throw Error('Comparison values must be numbers for this factor.');

  const seedText = $('seeds').value.trim();
  let seeds;

  if (/^\d+\s*-\s*\d+$/.test(seedText)) {
    const [a, b] = seedText.split('-').map(Number);

    if (b < a || b - a > 19)
      throw Error('Seed range must contain 1–20 increasing seeds.');

    seeds = Array.from({
      length: b - a + 1
    }, (_, i) => a + i);
  } else
    seeds = seedText.split(',').map(x => Number(x.trim()));

  if (seeds.some(x => !Number.isInteger(x) || x < 0))
    throw Error('Seeds must be nonnegative integers.');

  return {
    basis: $('basis').value,
    parameter,
    values,
    seeds
  };
}

function comparisonKey() {
  return JSON.stringify({
    config: draft,
    design: reviewDesign()
  });
}

async function previewComparison() {
  try {
    notice('Validating every arm, capacity and staging footprint…');

    const design = reviewDesign(),
          r = await api('/api/compare/validate', {
            config: draft,
            design
          });

    comparisonCheck = comparisonKey();
    $('runComparison').disabled = false;

    $('comparisonReview').innerHTML = `<h3>${r.total_runs} fresh Python runs</h3><div class="table-scroll"><table><thead><tr><th>Arm</th><th>Vehicles</th><th>Cargo trucks</th><th>People</th><th>Total load (kg)</th><th>Load / truck (kg)</th></tr></thead><tbody>${r.arms.map(
  a => `<tr><td>${esc(a.name)}</td><td>${a.summary.total_vehicles}</td><td>${a.summary.cargo_trucks}</td><td>${a.summary.crew}</td><td>${fmt(a.summary.loaded_kg)}</td><td>${fmt(a.summary.effective_payload_kg)}</td></tr>`
).join('')}</tbody></table></div>${r.warnings.map(x => '<p class="hint">' + esc(x) + '</p>').join('')}`;

    notice('Comparison is valid. Review the arms and basis, then start.');
  } catch (e) {
    comparisonCheck = null;
    $('runComparison').disabled = true;
    notice(e.message, true);
  }
}

function renderComparison(id, r) {
  $('comparisonResults').hidden = false;

  const keys = [
    ['cargo_delivered', 'Delivered (t)'],
    ['delivered_frac', 'Delivered fraction'],
    ['crew_steps_at_risk', 'Exposure (crew-steps)'],
    ['crew_lost', 'Crew lost'],
    ['blue_losses', 'Vehicle losses'],
    ['mission_time', 'Time (s)'],
    ['cargo_success', 'Cargo success rate']
  ];

  $('comparisonResults').innerHTML = `<h2>Completed comparison · ${r.runs.length} runs</h2><p class="hint">Saved job ${id.slice(0, 8)} · factor ${esc(r.parameter)} · seeds ${r.seeds.join(', ')} · basis ${esc(r.basis)}. These results use the job's saved map/configuration, not later draft changes. Individual run replay is a trajectory, not a mean movie. CI unavailable with one seed.</p><label>Reported outcome<select id="comparisonMetric">${keys.map(([k, t]) => `<option value="${k}">${esc(t)}</option>`).join('')}</select></label><div id="statsTable"></div><p class="hint">${r.warnings.map(esc).join(' ')} Intervals containing zero do not prove equivalence. A zero-width interval reflects observed sample variation only.</p><div class="buttons"><button id="downloadComparison">Download comparison JSON</button></div><details><summary>Individual runs · inspect a seed</summary><div class="table-scroll"><table><thead><tr><th>Arm</th><th>Seed</th><th>Load (kg)</th><th>Delivered (t)</th><th>In transit (t)</th><th>Replay</th></tr></thead><tbody>${r.runs.map(
  row => `<tr><td>${esc(row.arm)}</td><td>${row.seed}</td><td>${fmt(row.summary.loaded_kg)}</td><td>${fmt(row.outcome.cargo_delivered)}</td><td>${fmt(row.outcome.cargo_in_transit)}</td><td><button data-run-index="${row.index}">Inspect</button></td></tr>`
).join('')}</tbody></table></div></details>`;

  const stats = () => {
    const key = $('comparisonMetric').value;

    $('statsTable').innerHTML = `<div class="table-scroll"><table><thead><tr><th>Arm</th><th>n</th><th>Mean</th><th>SD</th><th>SE</th><th>Paired Δ vs baseline</th><th>Paired 95% t interval</th></tr></thead><tbody>${r.statistics.map(a => {
  const s = a.metrics[key];
  return `<tr><td>${esc(a.arm)}</td><td>${s.n}</td><td>${fmt(s.mean, 4)}</td><td>${s.sd === null ? '—' : fmt(s.sd, 4)}</td><td>${s.se === null ? '—' : fmt(s.se, 4)}</td><td>${a.arm === 'baseline' ? 'Reference' : fmt(s.paired_difference, 4)}</td><td>${a.arm === 'baseline' ? 'Reference' : s.paired_ci95 ? s.paired_ci95.map(x => fmt(x, 4)).join(' to ') : 'Not estimable (n=1)'}</td></tr>`;
}).join('')}</tbody></table></div>`;
  };

  $('comparisonMetric').onchange = stats;
  stats();
  $('downloadComparison').onclick = () => download('v3-comparison-' + id.slice(0, 8) + '.json', r);
  $('comparisonResults').querySelectorAll('[data-run-index]').forEach(b => b.onclick = () => loadRun(id, Number(b.dataset.runIndex)));
}

function basisHint() {
  $('basisHint').textContent = $('basis').value === 'same_fleet' ? 'Same fleet keeps role counts and vehicle composition fixed. A payload factor can change the loaded cargo; that changes the delivery task. Fleet-size factors require Same initial loaded cargo.' : 'Same initial loaded cargo reallocates the baseline mass equally across cargo trucks, subject to capacity. More trucks can carry less each. Staging must fit every arm without silently moving the lead.';
}
