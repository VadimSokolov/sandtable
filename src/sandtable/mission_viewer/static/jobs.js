'use strict';
async function startJob(kind) {
  if (activeJob && ['queued', 'running'].includes(activeJob.state)) {
    notice('A job is already active in this page. Cancel or wait, or reopen it from Saved V3 jobs.', true);
    return;
  }

  try {
    if (kind === 'run' && !validated)
      throw Error('Validate and review the current draft first.');

    if (kind === 'comparison' && comparisonKey() !== comparisonCheck)
      throw Error('Comparison changed. Validate it again first.');

    playing = false;

    const r = await api(kind === 'run' ? '/api/run' : '/api/compare', {
      config: clone(draft),

      ...(kind === 'comparison' ? {
        design: reviewDesign()
      } : {})
    });

    artifact = null;
    artifactJob = null;

    activeJob = {
      id: r.id,
      state: r.state,
      kind
    };

    $('run').disabled = true;
    $('runComparison').disabled = true;
    $('jobProgress').hidden = false;
    $('runHeading').textContent = kind === 'run' ? 'Executing a new Python mission.' : 'Executing the declared comparison.';
    $('runDescription').textContent = 'The job uses an immutable configuration snapshot. Editing a draft cannot change a running mission.';
    selectTab('run');
    notice('New job ' + r.id.slice(0, 8) + ' started. This is not a cached replay.');
    pollJob(r.id);
  } catch (e) {
    notice(e.message, true);
  }
}

async function pollJob(id) {
  try {
    const s = await api('/api/jobs/' + id);

    if (activeJob?.id !== id)
      return;

    activeJob = {
      ...activeJob,
      ...s
    };

    $('jobState').textContent = s.state.toUpperCase();
    $('jobCount').textContent = `${s.completed} / ${s.total} completed`;
    $('jobBar').value = s.fraction || 0;
    $('jobMessage').textContent = s.message + (s.tick !== undefined ? ' · step ' + s.tick : '');
    $('cancelJob').disabled = !['queued', 'running'].includes(s.state);

    if (['queued', 'running'].includes(s.state)) {
      jobTimer = setTimeout(() => pollJob(id), 450);
      return;
    }

    $('run').disabled = !validated;
    $('runComparison').disabled = !comparisonCheck;
    await refreshHistory();

    if (s.state === 'complete') {
      const r = await api('/api/jobs/' + id + '/result');

      if (r.kind === 'run') {
        await loadRun(id, 0);
        notice('New Python run complete. The replay starts at time 0; final outcome is separate.');
      } else {
        renderComparison(id, r);
        selectTab('compare');
        notice('Comparison complete. Every result comes from a fresh run of the declared map.');
      }
    } else
      notice(s.message, s.state === 'failed');
  } catch (e) {
    notice('Job status could not be read: ' + e.message, true);
  }
}

async function refreshHistory() {
  try {
    const jobs = await api('/api/jobs');

    $('history').innerHTML = jobs.map(
      j => `<div class="history-item"><b>${esc(j.name)}</b><small>${esc(j.kind)} · ${esc(j.state)} · ${j.completed}/${j.total} · ${j.id.slice(0, 8)}</small><div class="buttons"><button data-open-job="${j.id}" data-kind="${j.kind}" data-state="${j.state}">${['running', 'queued'].includes(j.state) ? 'Monitor' : j.state === 'complete' ? 'Open result' : 'View status'}</button><button data-restore-job="${j.id}">Restore inputs</button></div></div>`
    ).join('') || '<p class="hint">No V3 jobs yet. V2 recordings remain in the archive.</p>';

    $('history').querySelectorAll('[data-open-job]').forEach(b => b.onclick = async () => {
      try {
        const id = b.dataset.openJob;

        if (b.dataset.kind === 'study') {
          selectTab('library');
          SavedScenarios.showJob(id);
          return;
        }

        if (['queued', 'running'].includes(b.dataset.state)) {
          activeJob = {
            id,
            kind: b.dataset.kind
          };

          $('jobProgress').hidden = false;
          selectTab('run');
          pollJob(id);
        } else if (b.dataset.state === 'complete') {
          const r = await api('/api/jobs/' + id + '/result');

          if (r.kind === 'run')
            await loadRun(id, 0);
          else {
            renderComparison(id, r);
            selectTab('compare');
          }
        } else {
          const s = await api('/api/jobs/' + id);
          notice(s.message, s.state === 'failed');
        }
      } catch (e) {
        notice(e.message, true);
      }
    });

    $('history').querySelectorAll('[data-restore-job]').forEach(b => b.onclick = async () => {
      try {
        const r = await api('/api/jobs/' + b.dataset.restoreJob + '/request');
        preset(r.config);
        notice('Saved input configuration restored as a draft. A new run will receive a new job ID.');
      } catch (e) {
        notice(e.message, true);
      }
    });
  } catch (e) {
    notice(e.message, true);
  }
}
