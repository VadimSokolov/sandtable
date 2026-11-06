'use strict';
function selectTab(t) {
  tab = t;
  document.body.classList.toggle('library-mode', t === 'library');

  if (t === 'library')
    SavedScenarios.refresh();

  $('roadGraphPanel').hidden = t !== 'map' || !validated;
  playing = false;
  $('play').textContent = 'Play';
  lastRendered = -1;
  document.querySelectorAll('[data-tab]').forEach(b => b.setAttribute('aria-selected', String(b.dataset.tab === t)));

  for (const key of ['map', 'config', 'run', 'compare', 'library'])
    $(key + 'Panel').hidden = key !== t;

  const replay = t === 'run' && artifact;

  for (const key of ['play', 'restart', 'stepBack', 'stepForward', 'restoreRun', 'timeline'])
    $(key).disabled = !replay;

  if (!replay) {
    $('clock').textContent = 'No replay selected';
    $('replayState').classList.remove('final');
    $('replayState').textContent = 'Select a completed recording, or wait for the current Python job to finish.';
  }

  $('followWrap').hidden = !replay;
  $('liveMetrics').hidden = !replay;
  $('telemetry').hidden = !replay;
  $('eventBox').hidden = !replay;
  $('outcomeBox').hidden = !replay;
  $('canvasMode').textContent = replay ? 'RECORDED PYTHON RUN · ' + artifactJob.slice(0, 8) : 'DRAFT MAP · NOT RUN';
  $('toolHint').hidden = t !== 'map';
  draw();

  if (replay)
    renderFrame();

  document.querySelector('.app').scrollIntoView({
    block: 'start',
    behavior: 'instant'
  });
}

function preset(c) {
  checkpoint();
  draft = clone(c);
  selection = null;
  pendingNode = null;
  artifact = null;
  cam = null;
  zoom = 1;
  forms();
  dirty();
  inspector();
  notice('Template loaded as an editable draft. Validate before running.');
  selectTab('map');
}

function download(name, obj) {
  const blob = new Blob([JSON.stringify(obj, null, 2)], {
    type: 'application/json'
  });

  const u = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = u;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(u), 5000);
}

function bind() {
  document.querySelectorAll('[data-tab]').forEach(b => b.onclick = () => selectTab(b.dataset.tab));
  document.querySelectorAll('[data-tool]').forEach(b => b.onclick = () => setTool(b.dataset.tool));

  $('finishRoad').onclick = () => {
    pendingNode = null;
    draw();
  };

  $('delete').onclick = deleteSelected;
  $('sketch').onclick = () => preset(bootstrap.default);
  $('blank').onclick = () => preset(bootstrap.blank);

  $('undo').onclick = () => {
    if (!historyStack.length)
      return;

    draft = historyStack.pop();
    selection = null;
    pendingNode = null;
    forms();
    dirty();
    inspector();
  };

  $('saveScenario').onclick = () => download('sandtable-v3-scenario.json', draft);
  $('importScenario').onclick = () => $('fileInput').click();

  $('fileInput').onchange = async e => {
    const file = e.target.files[0];

    if (!file)
      return;

    try {
      if (file.size > 2000000)
        throw Error('Scenario JSON must be under 2 MB.');

      const c = JSON.parse(await file.text());

      if (c.schema_version !== 1 || !c.map || !c.mission)
        throw Error('Not a V3 scenario file.');

      const r = await api('/api/import', {
        config: c
      });

      preset(r.config);
      notice('Scenario opened as an editable draft. Validate when ready; no simulation was started.');
    } catch (err) {
      notice('Could not open scenario: ' + err.message, true);
    }

    e.target.value = '';
  };

  for (const [id, key] of [['worldWidth', 'width'], ['worldHeight', 'height'], ['goalRadius', 'goal_radius']]) $(id).onchange = () => {
    checkpoint();
    draft.map[key] = Number($(id).value);
    cam = null;
    dirty();
  };

  $('missionName').onchange = () => {
    checkpoint();
    draft.name = $('missionName').value;
    dirty();
  };

  $('routeAlgorithm').onchange = () => {
    checkpoint();
    draft.map.route_algorithm = $('routeAlgorithm').value;
    dirty();
  };

  $('roadPicker').onchange = () => {
    selection = $('roadPicker').value ? {type: 'road', id: $('roadPicker').value} : null;
    setTool('select');
    if (tab !== 'map') selectTab('map');
    inspector();
    $('inspector').closest('section').scrollIntoView({block: 'start', behavior: 'instant'});
  };

  $('autoExposure').onclick = () => {
    checkpoint();
    draft.map.roads.forEach(r => r.exposure_mode = 'auto');
    dirty();
    inspector();
  };

  $('routeMode').onchange = () => {
    checkpoint();
    draft.map.route_mode = $('routeMode').value;
    syncMapFields();
    dirty();
  };

  $('manualPath').onchange = () => {
    checkpoint();
    draft.map.manual_path = $('manualPath').value.split(',').map(x => x.trim()).filter(Boolean);
    dirty();
  };

  $('routeBias').oninput = () => {
    draft.map.route_bias = Number($('routeBias').value);
    $('biasValue').textContent = fmt(draft.map.route_bias);
    dirty();
  };

  const paths = {
    direct: ['START', 'JUNCTION', 'JOIN', 'GOAL'],
    upper: ['START', 'JUNCTION', 'UPPER_W', 'UPPER_E', 'JOIN', 'GOAL'],
    lower: ['START', 'JUNCTION', 'LOWER_W', 'LOWER_E', 'JOIN', 'GOAL']
  };

  for (const [id, path] of Object.entries(paths)) $(id).onclick = () => {
    if (path.some(key => !draft.map.nodes.find(n => n.id === key))) {
      notice(
        'This named path belongs to the sketch template. Choose Auto for your edited graph, or enter its node IDs.',
        true
      );

      return;
    }

    checkpoint();
    draft.map.route_mode = 'manual';
    draft.map.manual_path = path;
    const a = draft.map.nodes.find(n => n.id === path[0]), b = draft.map.nodes.find(n => n.id === path.at(-1));
    draft.map.start = [a.x, a.y];
    draft.map.goal = [b.x, b.y];
    syncMapFields();
    dirty();
  };

  $('validate').onclick = validate;
  $('run').onclick = () => startJob('run');
  $('previewComparison').onclick = previewComparison;
  $('runComparison').onclick = () => startJob('comparison');

  $('cancelJob').onclick = async () => {
    if (!activeJob)
      return;

    try {
      await api('/api/jobs/' + activeJob.id + '/cancel', {});
      $('jobMessage').textContent = 'Cancellation requested; waiting for the next simulation step.';
      $('cancelJob').disabled = true;
    } catch (e) {
      notice(e.message, true);
    }
  };

  $('refreshHistory').onclick = refreshHistory;
  $('factor').innerHTML = Object.entries(factorNames).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join('');

  for (const id of ['basis', 'factor', 'values', 'seeds']) $(id).onchange = () => {
    comparisonCheck = null;
    $('runComparison').disabled = true;
    $('comparisonResults').hidden = true;

    if (id === 'factor') {
      const k = $('factor').value;

      $('values').value = {
        pace: '8, 12',
        time_gap: '3, 6',
        min_gap: '20, 60',
        vehicles_per_unit: '4, 6',
        units_per_serial: '2, 4',
        serials: '2',
        escorts: '0, 6',
        payload_kg: '2500, 5000',
        response: 'continue, herringbone',
        leader_loss: 'continue, halt',
        comms: '2, 5'
      }[k];
    }

    basisHint();
  };

  basisHint();

  $('play').onclick = () => {
    if (!artifact)
      return;

    if (frameIndex === artifact.frames.length - 1)
      seek(0);

    playing = !playing;
    lastTime = null;
    $('play').textContent = playing ? 'Pause' : 'Play';
  };

  $('restart').onclick = () => {
    playing = false;
    $('play').textContent = 'Play';
    seek(0);
  };

  $('stepBack').onclick = () => {
    playing = false;
    $('play').textContent = 'Play';
    frameIndex = Math.max(0, frameIndex - 1);
    playTime = artifact.frames[frameIndex].t;
    renderFrame();
  };

  $('stepForward').onclick = () => {
    playing = false;
    $('play').textContent = 'Play';
    frameIndex = Math.min(artifact.frames.length - 1, frameIndex + 1);
    playTime = artifact.frames[frameIndex].t;
    renderFrame();
  };

  $('timeline').oninput = () => {
    playing = false;
    $('play').textContent = 'Play';
    seek($('timeline').value);
  };

  $('follow').onchange = () => {
    follow = Number($('follow').value);
    draw();
  };

  $('fit').onclick = () => {
    follow = -1;
    $('follow').value = '-1';
    resetView();
  };

  $('zoomIn').onclick = () => changeZoom(1.5);
  $('zoomOut').onclick = () => changeZoom(1 / 1.5);
  $('rings').onchange = draw;

  $('restoreRun').onclick = () => {
    if (artifact)
      preset(artifact.configuration);
  };

  $('exportRun').onclick = () => {
    if (artifact)
      download('v3-run-' + artifactJob.slice(0, 8) + '-seed-' + artifact.seed + '.json', artifact);
  };

  document.addEventListener('keydown', e => {
    if (['INPUT', 'SELECT', 'TEXTAREA'].includes(e.target.tagName))
      return;

    if (e.key === 'Escape') {
      pendingNode = null;
      drag = null;
      setTool('select');
    }

    if ((e.key === 'Delete' || e.key === 'Backspace') && tab === 'map') {
      e.preventDefault();
      deleteSelected();
    }
  });
}

async function init() {
  try {
    bootstrap = await api('/api/bootstrap');
    draft = clone(bootstrap.default);

    try {
      const saved = JSON.parse(localStorage.getItem('sandtable-v3-draft'));

      if (saved?.schema_version === 1 && saved.map && saved.mission)
        draft = saved;
    } catch {}

    $('enginePath').textContent = bootstrap.engine;
    bind();
    forms();
    renderFleet();
    syncMapFields();
    setTool('select');

    SavedScenarios.init({
      loadConfig: (c, view) => {
        preset(c);
        selectTab(view);
      },

      replay: (id, index) => {
        $('jobProgress').hidden = true;
        loadRun(id, index);
      },

      error: m => notice(m, true),
      download
    });

    await refreshHistory();
    draw();
    requestAnimationFrame(animate);

    if (location.hash === '#library')
      selectTab('library');
  } catch (e) {
    notice('V3 could not initialize: ' + e.message, true);
  }
}

init();

$('showRoadGraph').onclick = async () => {
  if (!validated)
    await validate();

  if (validated) {
    $('roadGraphPanel').hidden = false;

    $('roadGraphPanel').scrollIntoView({
      block: 'start',
      behavior: 'smooth'
    });
  }
};
