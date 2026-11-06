'use strict';
let redDefault = 1000;
const canvas = $('mapCanvas'), ctx = canvas.getContext('2d');

let size = {
      w: 900,
      h: 450
    },
    transform = {
      scale: 1,
      ox: 0,
      oy: 0
    };

const palette = {
  ink: '#183847',
  road: '#d7e2e6',
  lane: '#fafcfc',
  teal: '#07827b',
  red: '#ba5147',
  building: '#a7b4ba',
  selected: '#d69b39',
  grey: '#8b9ca5'
};

function currentMap() {
  return tab === 'run' && artifact ? artifact.configuration.map : draft.map;
}

function resetView() {
  zoom = 1;
  cam = null;
  draw();
}

function project(p) {
  return [transform.ox + p[0] * transform.scale, transform.oy - p[1] * transform.scale];
}

function unproject(x, y) {
  return [(x - transform.ox) / transform.scale, (transform.oy - y) / transform.scale];
}

function cLine(a, b, color, width = 1, dash = []) {
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.setLineDash(dash);
  ctx.beginPath();
  ctx.moveTo(...a);
  ctx.lineTo(...b);
  ctx.stroke();
  ctx.setLineDash([]);
}

function cText(x, y, text, color = palette.ink, font = 11) {
  ctx.font = `${font}px -apple-system,BlinkMacSystemFont,Arial,sans-serif`;
  ctx.fillStyle = color;
  ctx.fillText(text, x, y);
}

function draw() {
  if (!draft)
    return;

  const box = canvas.getBoundingClientRect();

  if (box.width < 1 || box.height < 1)
    return;

  const dpr = window.devicePixelRatio || 1;

  if (canvas.width !== Math.round(box.width * dpr) || canvas.height !== Math.round(box.height * dpr)) {
    canvas.width = Math.round(box.width * dpr);
    canvas.height = Math.round(box.height * dpr);
  }

  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  size = {
    w: box.width,
    h: box.height
  };

  ctx.clearRect(0, 0, size.w, size.h);
  ctx.fillStyle = '#fafcfc';
  ctx.fillRect(0, 0, size.w, size.h);
  const m = currentMap(), scale = Math.min((size.w - 52) / m.width, (size.h - 48) / m.height) * zoom;

  if (!cam)
    cam = [m.width / 2, m.height / 2];

  const replay = tab === 'run' && artifact, f = replay ? artifact.frames[frameIndex] : null;

  if (replay && follow >= 0 && f)
    cam = [f.x[follow], f.y[follow]];

  transform = {
    scale,
    ox: size.w / 2 - cam[0] * scale,
    oy: size.h / 2 + cam[1] * scale
  };

  $('zoomLabel').textContent = fmt(zoom, 1) + '×';
  const grid = Math.max(100, Math.pow(10, Math.ceil(Math.log10(m.width / 8))));

  for (let x = 0; x <= m.width; x += grid) {
    const a = project([x, 0]), b = project([x, m.height]);
    cLine(a, b, '#e8eef0');

    if (a[0] > 0 && a[0] < size.w - 30)
      cText(a[0] + 3, Math.min(size.h - 7, a[1] + 15), fmt(x), '#82939a', 9);
  }

  for (let y = 0; y <= m.height; y += grid)
    cLine(project([0, y]), project([m.width, y]), '#e8eef0');

  const ns = new Map(m.nodes.map(n => [n.id, n]));

  for (const r of m.roads) {
    const u = ns.get(r.u), v = ns.get(r.v);

    if (!u || !v)
      continue;

    cLine(
      project([u.x, u.y]),
      project([v.x, v.y]),
      selection?.type === 'road' && selection.id === r.id ? palette.selected : palette.road,
      Math.max(3, r.width * scale)
    );

    cLine(project([u.x, u.y]), project([v.x, v.y]), '#aebfc5', 1, [6, 7]);
  }

  for (const b of m.buildings) {
    const p = project([b.box[0], b.box[3]]);
    ctx.fillStyle = selection?.type === 'building' && selection.id === b.id ? palette.selected : palette.building;
    ctx.fillRect(p[0], p[1], (b.box[2] - b.box[0]) * scale, (b.box[3] - b.box[1]) * scale);

    if ((b.box[2] - b.box[0]) * scale > 25)
      cText(p[0] + 5, p[1] + 14, b.id, '#314956', 10);
  }

  const route = replay ? artifact.summary.route : validated?.summary.route;

  if (route?.length) {
    ctx.strokeStyle = palette.teal;
    ctx.lineWidth = 2.5;
    ctx.beginPath();

    route.forEach((p, i) => {
      const q = project(p);
      i ? ctx.lineTo(...q) : ctx.moveTo(...q);
    });

    ctx.stroke();
  }

  if (!replay) {
    for (const n of m.nodes) {
      const p = project([n.x, n.y]);
      ctx.fillStyle = selection?.type === 'node' && selection.id === n.id ? palette.selected : palette.ink;
      ctx.beginPath();
      ctx.arc(...p, 3.5, 0, Math.PI * 2);
      ctx.fill();
      cText(p[0] + 6, p[1] - 6, n.id, palette.ink, 10);
    }
  }

  if (!replay && validated) {
    const originalIds = new Set(m.nodes.map(n => n.id));

    for (const n of validated.summary.graph.nodes) {
      if (originalIds.has(n.id))
        continue;

      const p = project([n.x, n.y]);
      ctx.strokeStyle = palette.teal;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(...p, 5, 0, Math.PI * 2);
      ctx.stroke();
      cText(p[0] + 7, p[1] - 7, n.id + ' · junction', palette.teal, 10);
    }
  }

  for (const e of m.red) {
    const p = project([e.x, e.y]);

    if ($('rings').checked) {
      ctx.strokeStyle = '#bd655d';
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 5]);
      ctx.beginPath();
      ctx.arc(...p, e.weapon_range * scale, 0, Math.PI * 2);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    ctx.save();
    ctx.translate(...p);
    ctx.rotate(Math.PI / 4);
    ctx.fillStyle = selection?.type === 'red' && selection.id === e.id ? palette.selected : palette.red;
    ctx.fillRect(-5, -5, 10, 10);
    ctx.restore();

    if (!replay)
      cText(p[0] + 9, p[1] - 7, e.id, palette.red, 10);
  }

  for (const [p, label, color] of [[m.start, 'START AREA', palette.teal], [m.goal, 'GOAL', palette.teal]]) {
    const q = project(p);
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(...q, 6, 0, Math.PI * 2);
    ctx.fill();
    cText(q[0] + 10, q[1] - 9, label, color, 10);
  }

  const gp = project(m.goal);
  ctx.strokeStyle = '#3f9a80';
  ctx.setLineDash([4, 4]);
  ctx.beginPath();
  ctx.arc(...gp, m.goal_radius * scale, 0, Math.PI * 2);
  ctx.stroke();
  ctx.setLineDash([]);

  if (!replay && validated) {
    validated.summary.spawn.forEach(
      (p, i) => vehicle(project(p), 0, validated.summary.roles[i] === 0 ? palette.ink : palette.teal, true, 0, i)
    );

    const lead = project(validated.summary.spawn[0]);
    cText(lead[0] - 5, lead[1] + 22, 'LEAD SPAWN', palette.teal, 10);
  }

  if (replay) {
    artifact.entities.forEach((e, i) => {
      const p = project([f.x[i], f.y[i]]);

      if (e.side === 0)
        vehicle(p, f.heading[i], e.role === 0 ? palette.ink : palette.teal, !!f.alive[i], f.speed[i], i);
      else if (!f.alive[i]) {
        cLine([p[0] - 5, p[1] - 5], [p[0] + 5, p[1] + 5], palette.red, 2);
        cLine([p[0] + 5, p[1] - 5], [p[0] - 5, p[1] + 5], palette.red, 2);
      }
    });
  }

  if (drag?.kind === 'building') {
    const a = project(drag.start), b = project(drag.now);
    ctx.strokeStyle = palette.teal;
    ctx.strokeRect(Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));
  }

  if (pendingNode && !replay) {
    const n = ns.get(pendingNode);

    if (n) {
      const p = project([n.x, n.y]);
      ctx.strokeStyle = palette.teal;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(...p, 9, 0, Math.PI * 2);
      ctx.stroke();
    }
  }

  ctx.strokeStyle = '#b2c2c8';
  const tl = project([0, m.height]);
  ctx.strokeRect(tl[0], tl[1], m.width * scale, m.height * scale);
  cText(12, 18, replay ? `PYTHON SNAPSHOT · ${fmt(f.t)} s` : 'DRAFT · metres', palette.ink, 10);
}

function vehicle(p, h, color, alive, speed, i) {
  ctx.save();
  ctx.translate(...p);

  if (!alive) {
    cLine([-5, -5], [5, 5], palette.red, 2);
    cLine([5, -5], [-5, 5], palette.red, 2);
  } else {
    ctx.rotate(-h);
    ctx.fillStyle = selection?.type === 'vehicle' && selection.id === i ? palette.selected : color;
    ctx.fillRect(-6, -3.5, 12, 7);
    ctx.fillStyle = '#b7d7d5';
    ctx.fillRect(3, -2.5, 2, 5);
  }

  ctx.restore();
}

new ResizeObserver(draw).observe(canvas);

function distancePoint(p, a, b) {
  const vx = b[0] - a[0], vy = b[1] - a[1], t = Math.max(0, Math.min(1, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / (vx * vx + vy * vy || 1)));
  const q = [a[0] + t * vx, a[1] + t * vy];

  return {
    point: q,
    distance: Math.hypot(p[0] - q[0], p[1] - q[1])
  };
}

function eventPoint(e) {
  const r = canvas.getBoundingClientRect();
  return unproject(e.clientX - r.left, e.clientY - r.top);
}

function bounded(p) {
  return [Math.max(1, Math.min(draft.map.width - 1, p[0])), Math.max(1, Math.min(draft.map.height - 1, p[1]))].map(x => Math.round(x));
}

function nextId(prefix, arr) {
  let i = 1;

  while (arr.some(x => x.id === prefix + i))
    i++;

  return prefix + i;
}

function nearestNode(p) {
  let best = null, d = 16 / transform.scale;

  for (const n of draft.map.nodes) {
    const q = Math.hypot(p[0] - n.x, p[1] - n.y);

    if (q < d) {
      d = q;
      best = n;
    }
  }

  return best;
}

function snapRoad(p) {
  const ns = new Map(draft.map.nodes.map(n => [n.id, n]));
  let best = null;

  for (const r of draft.map.roads) {
    const a = ns.get(r.u), b = ns.get(r.v);

    if (!a || !b)
      continue;

    const q = distancePoint(p, [a.x, a.y], [b.x, b.y]);

    if (q.distance <= Math.max(r.width / 2, 8 / transform.scale) && (!best || q.distance < best.distance))
      best = q;
  }

  return best ? best.point.map(x => Math.round(x * 100) / 100) : p;
}

function hit(p) {
  const m = currentMap(), r = 14 / transform.scale;

  if (tab === 'run' && artifact) {
    const f = artifact.frames[frameIndex];
    let k = -1, d = r;

    f.x.forEach((x, i) => {
      const a = Math.hypot(p[0] - x, p[1] - f.y[i]);

      if (a < d) {
        d = a;
        k = i;
      }
    });

    return k >= 0 ? {
      type: 'vehicle',
      id: k
    } : null;
  }

  for (const type of ['start', 'goal']) if (Math.hypot(p[0] - m[type][0], p[1] - m[type][1]) < r) return {
    type,
    id: type
  };

  for (const e of m.red) if (Math.hypot(p[0] - e.x, p[1] - e.y) < r) return {
    type: 'red',
    id: e.id
  };

  for (const n of m.nodes) if (Math.hypot(p[0] - n.x, p[1] - n.y) < r) return {
    type: 'node',
    id: n.id
  };

  if (validated) {
    const originalIds = new Set(m.nodes.map(n => n.id));

    for (const n of validated.summary.graph.nodes) if (!originalIds.has(n.id) && Math.hypot(p[0] - n.x, p[1] - n.y) < r) return {
      type: 'junction',
      id: n.id
    };
  }

  for (const b of m.buildings) if (p[0] >= b.box[0] && p[0] <= b.box[2] && p[1] >= b.box[1] && p[1] <= b.box[3]) return {
    type: 'building',
    id: b.id
  };

  const ns = new Map(m.nodes.map(n => [n.id, n]));

  for (const e of m.roads) {
    const a = ns.get(e.u), b = ns.get(e.v);

    if (a && b && distancePoint(p, [a.x, a.y], [b.x, b.y]).distance < Math.max(e.width / 2, 8 / transform.scale)) return {
      type: 'road',
      id: e.id
    };
  }

  return null;
}

function object() {
  if (!selection)
    return null;

  const t = selection.type;

  if (t === 'start' || t === 'goal')
    return draft.map[t];

  const key = {
    node: 'nodes',
    road: 'roads',
    building: 'buildings',
    red: 'red'
  }[t];

  return key ? draft.map[key].find(x => x.id === selection.id) : null;
}

canvas.onpointerdown = e => {
  if (e.button !== 0)
    return;

  const p = tab === 'run' && artifact ? eventPoint(e) : bounded(eventPoint(e));
  canvas.setPointerCapture(e.pointerId);

  if (tab === 'run' && artifact) {
    selection = hit(p);
    inspector();

    if (!selection) {
      follow = -1;
      $('follow').value = '-1';

      drag = {
        kind: 'pan',
        client: [e.clientX, e.clientY],
        cam: [...cam]
      };
    }

    draw();
    return;
  }

  if (tab !== 'map') {
    drag = {
      kind: 'pan',
      client: [e.clientX, e.clientY],
      cam: [...cam]
    };

    return;
  }

  if (tool === 'road') {
    checkpoint();
    let node = nearestNode(p);

    if (!node) {
      node = {
        id: nextId('N', draft.map.nodes),
        x: p[0],
        y: p[1]
      };

      draft.map.nodes.push(node);
    }

    if (pendingNode && pendingNode !== node.id && !draft.map.roads.some(r => r.u === pendingNode && r.v === node.id || r.v === pendingNode && r.u === node.id)) draft.map.roads.push({
      id: nextId('R', draft.map.roads),
      u: pendingNode,
      v: node.id,
      width: 100,
      speed_mult: 1,
      exposure: .5,
      exposure_mode: 'auto'
    });

    pendingNode = node.id;
    draft.map.route_mode = 'auto';
    syncMapFields();

    selection = {
      type: 'node',
      id: node.id
    };

    dirty();
    inspector();
    return;
  }

  if (tool === 'building') {
    checkpoint();

    drag = {
      kind: 'building',
      start: p,
      now: p
    };

    return;
  }

  if (tool === 'red') {
    checkpoint();

    const x = {
      id: nextId('E', draft.map.red),
      x: p[0],
      y: p[1],
      weapon_range: redDefault,
      sensor_range: 2000,
      pk: .008
    };

    draft.map.red.push(x);

    selection = {
      type: 'red',
      id: x.id
    };

    dirty();
    inspector();
    return;
  }

  if (tool === 'start' || tool === 'goal') {
    checkpoint();
    draft.map[tool] = snapRoad(p);
    draft.map.route_mode = 'auto';

    selection = {
      type: tool,
      id: tool
    };

    syncMapFields();
    dirty();
    inspector();
    return;
  }

  selection = hit(p);
  inspector();

  if (selection && ['node', 'building', 'red', 'start', 'goal'].includes(selection.type)) {
    checkpoint();

    drag = {
      kind: 'object',
      start: p,
      original: clone(object()),

      selection: {
        ...selection
      }
    };
  } else if (!selection) drag = {
    kind: 'pan',
    client: [e.clientX, e.clientY],
    cam: [...cam]
  };

  draw();
};

canvas.onpointermove = e => {
  const p = eventPoint(e);
  $('pointerPos').textContent = `x=${fmt(p[0], 0)} m · y=${fmt(p[1], 0)} m`;

  if (!drag)
    return;

  if (drag.kind === 'pan') {
    cam = [
      drag.cam[0] - (e.clientX - drag.client[0]) / transform.scale,
      drag.cam[1] + (e.clientY - drag.client[1]) / transform.scale
    ];

    draw();
    return;
  }

  if (drag.kind === 'building') {
    drag.now = bounded(p);
    draw();
    return;
  }

  if (drag.kind === 'object') {
    const q = bounded(p), dx = q[0] - drag.start[0], dy = q[1] - drag.start[1], o = drag.original, t = selection.type;

    if (t === 'start' || t === 'goal')
      draft.map[t] = bounded([o[0] + dx, o[1] + dy]);
    else if (t === 'building') {
      const b = object();
      b.box = [o.box[0] + dx, o.box[1] + dy, o.box[2] + dx, o.box[3] + dy].map(x => Math.round(x));
    } else {
      const x = object();
      [x.x, x.y] = bounded([o.x + dx, o.y + dy]);
    }

    dirty();
    inspector();
  }
};

function finishDrag() {
  if (!drag)
    return;

  if (drag.kind === 'building') {
    const a = drag.start, b = drag.now, box = [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[0], b[0]), Math.max(a[1], b[1])];

    if (box[2] - box[0] >= 5 && box[3] - box[1] >= 5) {
      const obj = {
        id: nextId('B', draft.map.buildings),
        box
      };

      draft.map.buildings.push(obj);

      selection = {
        type: 'building',
        id: obj.id
      };

      dirty();
      inspector();
    }
  }

  if (drag.kind === 'object' && ['start', 'goal'].includes(selection.type)) {
    draft.map[selection.type] = snapRoad(draft.map[selection.type]);
    draft.map.route_mode = 'auto';
    syncMapFields();
    dirty();
  }

  drag = null;
  draw();
}

canvas.onpointerup = finishDrag;
canvas.onpointercancel = finishDrag;

function changeZoom(factor) {
  zoom = Math.max(1, Math.min(24, zoom * factor));
  draw();
}

canvas.addEventListener('wheel', e => {
  e.preventDefault();
  changeZoom(e.deltaY < 0 ? 1.2 : 1 / 1.2);
}, {
  passive: false
});

function inspector() {
  $('roadPicker').value = selection?.type === 'road' ? selection.id : '';
  if (selection?.type === 'junction') {
    const n = validated?.summary.graph.nodes.find(n => n.id === selection.id);
    $('inspector').innerHTML = n ? `<h3>${esc(n.id)} · generated crossing</h3><p>x=${fmt(n.x)} m, y=${fmt(n.y)} m. Connected by validation. Move the original road endpoints to edit this junction.</p>` : 'Select a road object.';
    return;
  }

  if (!selection) {
    $('inspector').textContent = 'Choose a road above, or select another object on the map.';
    return;
  }

  if (selection.type === 'vehicle' && artifact) {
    const e = artifact.entities[selection.id], f = artifact.frames[frameIndex], i = selection.id, roles = ['Control', 'Cargo', 'Escort', 'Recovery'];

    $('inspector').innerHTML = `<h3>${esc(e.label)} · ${e.side === 0 ? roles[e.role] : 'Red'}</h3><div class="review-list">${[
  ['Alive', f.alive[i] ? 'Yes' : 'No'],
  ['Position', fmt(f.x[i]) + ', ' + fmt(f.y[i]) + ' m'],
  ['Actual speed', fmt(f.speed[i]) + ' m/s'],
  [
    'Tracked reference speed',
    f.tracked_reference_speed ? fmt(f.tracked_reference_speed[i]) + ' m/s' : 'Not recorded'
  ],
  ['Movement state', f.motion_reason?.[i] || 'Not recorded'],
  ['Control quality', fmt(f.quality[i], 4)],
  ['Crew assigned', e.crew],
  ['Original cargo', fmt(e.cargo_kg) + ' kg'],
  ['Leader', f.leader[i] < 0 ? 'No parent' : 'V' + (f.leader[i] + 1)],
  ['Contact hold', f.contact_hold[i] ? 'Yes' : 'No'],
  ['Leader-loss hold', f.leader_hold[i] ? 'Yes' : 'No'],
  ['Geometry constrained', f.constraint[i] ? 'Yes' : 'No']
].map(([k, v]) => `<span>${esc(k)}</span><b>${esc(v)}</b>`).join('')}</div>`;

    return;
  }

  if (tab === 'run' && artifact) {
    $('inspector').textContent = 'Click a vehicle to inspect its current state.';
    return;
  }

  const o = object();

  if (!o) {
    selection = null;
    return inspector();
  }

  const type = selection.type;
  if (type === 'road') {
    const id = selection.id;
    new RoadEditor($('inspector'), o, {
      routeReady: Boolean(validated),
      routing: validated?.summary.routing,
      onChange: (patch, redraw) => {
        const road = draft.map.roads.find(r => r.id === id);
        if (!road) return;
        checkpoint();
        Object.assign(road, patch);
        dirty();
        if (redraw) inspector();
      },
      onReplan: async () => {
        checkpoint();
        draft.map.route_mode = 'auto';
        syncMapFields();
        dirty();
        await validate();
        inspector();
        $('inspector').closest('section').scrollIntoView({block: 'start', behavior: 'instant'});
      }
    }).render();
    return;
  }
  let edits = [];

  if (type === 'node' || type === 'red')
    edits = [['x', 'x (m)', o.x], ['y', 'y (m)', o.y]];

  if (type === 'red') edits.push(
    ['weapon_range', 'Weapon range (m)', o.weapon_range],
    ['sensor_range', 'Sensor range (m)', o.sensor_range],
    ['pk', 'Base damage probability', o.pk]
  );

  if (type === 'building')
    edits = o.box.map((v, i) => ['box' + i, ['Min x', 'Min y', 'Max x', 'Max y'][i] + ' (m)', v]);

  if (type === 'start' || type === 'goal')
    edits = [['x', 'x (m)', o[0]], ['y', 'y (m)', o[1]]];

  $('inspector').innerHTML = `<h3>${esc(type)} · ${esc(selection.id)}</h3>${type === 'start' ? '<p>Rear origin of the starting road area. Lead placement uses the fixed staging offset, not this point itself.</p>' : ''}<div class="inspector-fields">${edits.map(
  ([k, t, v]) => `<label>${esc(t)}<input type="number" data-edit="${k}" value="${v}" step="any"></label>`
).join('')}</div>`;

  $('inspector').querySelectorAll('[data-edit]').forEach(el => el.onchange = () => {
    checkpoint();
    const k = el.dataset.edit, v = Number(el.value);

    if (type === 'start' || type === 'goal')
      draft.map[type][k === 'x' ? 0 : 1] = v;
    else if (type === 'building')
      o.box[Number(k.slice(3))] = v;
    else
      o[k] = v;

    dirty();
    inspector();
  });
}

function deleteSelected() {
  if (tab !== 'map' || !selection)
    return;

  checkpoint();

  const {
    type,
    id
  } = selection;

  if (type === 'start' || type === 'goal') {
    notice('Move this marker; it cannot be deleted.', true);
    return;
  }

  const key = {
    node: 'nodes',
    road: 'roads',
    building: 'buildings',
    red: 'red'
  }[type];

  if (!key)
    return;

  draft.map[key] = draft.map[key].filter(x => x.id !== id);

  if (type === 'node') {
    draft.map.roads = draft.map.roads.filter(x => x.u !== id && x.v !== id);
    draft.map.manual_path = draft.map.manual_path.filter(x => x !== id);
    draft.map.route_mode = 'auto';
    pendingNode = null;
  }

  selection = null;
  syncMapFields();
  dirty();
  inspector();
}

const toolHints = {
  select: 'Select a node, road, building or Red site to inspect it. Drag nodes, buildings or markers to move them.',
  road: 'Click the first node, then click subsequent points to connect roads. Existing nodes snap within 16 px. Crossings become connected junctions at validation. Finish road ends the chain.',
  building: 'Drag from one corner to the opposite corner. Rectangles are obstacles for raster LOS and V3 movement guards.',
  start: 'Click on a road to place the rear start-area origin. The lead is placed staging_m ahead along the selected route; all vehicles must fit behind it.',
  goal: 'Click on a road to place the delivery goal. Goal radius is editable above.',
  red: 'Click to place a static Red site. Its weapon range and other assumptions are editable in Inspector.'
};

function setTool(t) {
  tool = t;
  pendingNode = null;
  document.querySelectorAll('[data-tool]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.tool === t)));
  $('toolHint').textContent = toolHints[t];
  canvas.style.cursor = t === 'select' ? 'default' : 'crosshair';
  draw();
}

let exposureTimer = null, exposureVersion = 0;

function scheduleExposure() {
  const version = ++exposureVersion;
  clearTimeout(exposureTimer);
  $('exposureStatus').textContent = 'Exposure preview pending…';

  exposureTimer = setTimeout(async () => {
    try {
      const x = await api('/api/exposure', {
        map: draft.map
      });

      if (version !== exposureVersion)
        return;

      for (const r of x.roads) {
        const o = draft.map.roads.find(q => q.id === r.id);

        if (o)
          o.exposure_auto = r.exposure_auto;
      }

      $('exposureStatus').textContent = 'Map estimates updated. Custom road scores are kept. Update the route to review the costs.';
      store();

      if (selection?.type === 'road' && !$('inspector').contains(document.activeElement))
        inspector();
    } catch (e) {
      if (version === exposureVersion)
        $('exposureStatus').textContent = 'Preview unavailable: ' + e.message;
    }
  }, 300);
}

setTimeout(() => {
  if (draft)
    scheduleExposure();
}, 500);
