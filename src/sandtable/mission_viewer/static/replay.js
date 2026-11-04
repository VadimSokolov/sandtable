'use strict';
async function loadRun(id, index) {
  try {
    const r = await api(`/api/jobs/${id}/runs/${index}`);
    artifact = r;
    artifactJob = id;
    frameIndex = 0;
    playTime = 0;
    playing = false;
    selection = null;
    follow = -1;
    zoom = 1;
    cam = null;
    lastRendered = -1;
    const labels = ['Control', 'Cargo', 'Escort', 'Recovery'];
    $('follow').innerHTML = '<option value="-1">Free camera</option>' + r.entities.map((e, i) => e.side === 0 ? `<option value="${i}">${esc(e.label)} · ${labels[e.role]}</option>` : '').join('');
    $('timeline').disabled = false;
    $('timeline').max = r.frames.at(-1).t;
    $('timeline').value = 0;

    for (const k of ['play', 'restart', 'stepBack', 'stepForward', 'restoreRun'])
      $(k).disabled = false;

    $('runHeading').textContent = r.configuration.name;
    $('runDescription').textContent = `Recorded Python run · ${r.arm} · seed ${r.seed} · job ${id.slice(0, 8)} · configuration ${r.config_hash.slice(0, 12)}. Camera shows the saved run's map, independent of the current draft.`;
    const o = r.outcome;

    $('outcome').innerHTML = `<p><b>Final result:</b> ${esc(r.end_reason)}</p><div class="review-list">${[
  ['Cargo requirement met', o.cargo_success ? 'Yes' : 'No'],
  ['Delivered', fmt(o.cargo_delivered * 1000) + ' kg'],
  ['Lost', fmt(o.cargo_lost * 1000) + ' kg'],
  ['In transit', fmt(o.cargo_in_transit * 1000) + ' kg'],
  ['Delivered fraction', fmt(o.delivered_frac * 100) + '%'],
  ['Crew lost', fmt(o.crew_lost)],
  ['Exposure', fmt(o.crew_steps_at_risk) + ' crew-steps'],
  ['Time', fmt(o.mission_time) + ' s'],
  ['Seed', r.seed]
].map(([a, b]) => `<span>${esc(a)}</span><b>${esc(b)}</b>`).join('')}</div><p class="mono">Configuration SHA-256: ${esc(r.config_hash)}<br>Engine revision: ${esc(r.provenance.revision)}<br>Source digest: ${esc(r.provenance.source_digest)}</p><p>Physical source hashes, configuration, resolved engine scenario and all recorded frames are included in the downloaded run.</p><details><summary>Raw outcome and model limits</summary><pre>${esc(JSON.stringify({
  notes: r.notes,
  definitions: r.summary.definitions,
  outcome: o
}, null, 2))}</pre></details>`;

    $('outcomeBox').open = false;
    selectTab('run');
    renderFrame();
    inspector();
  } catch (e) {
    notice(e.message, true);
  }
}

function renderFrame() {
  if (!artifact)
    return;

  const f = artifact.frames[frameIndex], end = frameIndex === artifact.frames.length - 1;
  $('timeline').value = f.t;
  $('clock').textContent = `T+${fmt(f.t)} / ${fmt(artifact.frames.at(-1).t)} s`;
  $('replayState').classList.toggle('final', end);
  $('replayState').textContent = end ? `FINAL SNAPSHOT · ${artifact.end_reason}` : 'REPLAY IN PROGRESS · Current snapshot only. The final mission outcome is not inferred from this frame.';
  const c = f.cargo;

  const stats = [
    ['Delivered', fmt(c.delivered * 1000) + ' kg'],
    ['Lost cargo', fmt(c.lost * 1000) + ' kg'],
    ['In transit', fmt(c.in_transit * 1000) + ' kg'],
    ['Living people', f.crew_alive],
    ['Crew lost', f.crew_lost],
    ['Exposure', fmt(f.exposure) + ' crew-steps'],
    ['Leaderless', f.leaderless_steps + ' unit-steps'],
    ['Handoffs', f.handoffs]
  ];

  $('liveMetrics').innerHTML = stats.map(([k, v]) => `<div><small>${esc(k)}</small><b>${esc(v)}</b></div>`).join('') + `<div class="cargo-balance"><b>Cargo balance</b><span>${fmt(c.loaded * 1000)} = ${fmt(c.delivered * 1000)} delivered + ${fmt(c.lost * 1000)} lost + ${fmt(c.in_transit * 1000)} in transit (kg)</span></div>`;
  const sum = a => a.reduce((x, y) => x + y, 0), con = f.consoles;
  $('telemetry').innerHTML = `<div class="telemetry-grid"><div><h3>Movement and leadership</h3><p>Contact: <b>${f.contact ? 'active' : 'clear'}</b> · contact hold commands: ${sum(f.contact_hold)} · leader-loss holds: ${sum(f.leader_hold)} · building/boundary constraints this step: ${sum(f.constraint)} · Herringbone parked: ${sum(f.parked)}.</p><p>Living heads: ${f.heads.map(h => h >= 0 && f.alive[h] ? 'V' + (h + 1) : 'none').join(', ')}. Initial route remains fixed.</p></div><div><h3>Console service</h3>${con ? `<p>Available hosts: ${con.available.map((ok, i) => `${i + 1}:${ok ? 'yes' : 'no'}`).join(' · ')}. Ownership: ${esc(con.rule)}.</p><p>Requests: ${sum(con.requests)} · accepted/scheduled service: ${sum(con.serviced)} · denied for host loss: ${sum(con.denied)}. These are not confirmed reply deliveries.</p>` : '<p>Initial snapshot, before the first console update.</p>'}<p>dt=1 s: exposure crew-steps numerically equals crew-seconds. This metric does not use LOS/detection.</p></div></div>`;
  const ev = artifact.events.filter(e => e.t <= f.t).slice(-150);

  $('events').innerHTML = ev.map(
    e => `<div class="event"><b>${fmt(e.t)} s</b><span>${esc(e.event)} ${e.vehicle !== undefined ? '· V' + (e.vehicle + 1) : ''}${e.console !== undefined ? ' · console ' + (e.console + 1) : ''}${e.heads ? ' · heads ' + e.heads.map(h => h < 0 ? 'none' : 'V' + (h + 1)).join(', ') : ''}${e.contact !== undefined ? ' · contact ' + (e.contact ? 'active' : 'clear') : ''}</span></div>`
  ).join('') || '<p>No events yet.</p>';

  draw();

  if (selection?.type === 'vehicle')
    inspector();
}

function seek(t) {
  if (!artifact)
    return;

  playTime = Number(t);
  let lo = 0, hi = artifact.frames.length - 1;

  while (lo < hi) {
    const mid = Math.ceil((lo + hi) / 2);

    if (artifact.frames[mid].t <= playTime)
      lo = mid;
    else
      hi = mid - 1;
  }

  frameIndex = lo;
  renderFrame();
}

function animate(stamp) {
  if (playing && artifact && tab === 'run') {
    if (lastTime !== null) {
      playTime += (stamp - lastTime) / 1000 * Number($('rate').value);
      const old = frameIndex;
      let lo = frameIndex, hi = artifact.frames.length - 1;

      while (lo < hi) {
        const mid = Math.ceil((lo + hi) / 2);

        if (artifact.frames[mid].t <= playTime)
          lo = mid;
        else
          hi = mid - 1;
      }

      frameIndex = lo;

      if (old !== frameIndex)
        renderFrame();

      if (playTime >= artifact.frames.at(-1).t) {
        playing = false;
        $('play').textContent = 'Play';
      }
    }
  }

  lastTime = stamp;
  requestAnimationFrame(animate);
}
