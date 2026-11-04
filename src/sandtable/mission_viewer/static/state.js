'use strict';
const $ = id => document.getElementById(id),
      clone = x => JSON.parse(JSON.stringify(x)),
      esc = s => String(s).replace(/[&<>"']/g, c => (({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        '\'': '&#39;'
      })[c])),
      fmt = (n, d = 2) => Number(n).toLocaleString('en-US', {
        maximumFractionDigits: d
      });

let bootstrap, draft, validated = null, comparisonCheck = null, tab = 'map', tool = 'select', selection = null, pendingNode = null, drag = null, historyStack = [], artifact = null, artifactJob = null, frameIndex = 0, playing = false, playTime = 0, lastTime = null, activeJob = null, jobTimer = null, follow = -1, zoom = 1, cam = null, lastRendered = -1;

const fields = [[
  'vehicles_per_unit',
  'Core vehicles / march unit',
  'number',
  2,
  25,
  1,
  'Excludes additional escorts.'
], ['units_per_serial', 'March units / serial', 'number', 2, 5, 1], ['serials', 'Serials', 'number', 1, 5, 1], [
  'escorts',
  'Additional escorts (total)',
  'number',
  0,
  30,
  1,
  'Distributed after control vehicles; not substituted for cargo.'
], [
  'layout',
  'Core role layout',
  'select',
  [['cargo', 'Control + cargo'], ['recovery', 'Control + cargo + recovery']]
], [
  'crew_mode',
  'Truck control mode',
  'select',
  [['supervised', 'Supervised autonomous cargo'], ['crewed', 'Crewed cargo']]
], [
  'payload_kg',
  'Loaded payload / truck (kg)',
  'number',
  1,
  50000,
  1,
  'Actual cargo load, not the capacity rating.'
], [
  'capacity_kg',
  'Cargo platform capacity (kg)',
  'number',
  1,
  50000,
  .00001,
  'Custom study platform; not an ATP vehicle designation.'
], ['pace', 'Commanded pace (m/s)', 'number', .1, 30, .5, 'Head speed cap. Actual speed can be lower.'], ['time_gap', 'Vehicle time gap (s)', 'number', .1, 60, .5], [
  'min_gap',
  'Minimum station gap (m)',
  'number',
  7,
  500,
  1,
  'Centre-reference separation, not bumper clearance.'
], [
  'response',
  'Movement response',
  'select',
  [['continue', 'Continue'], ['halt', 'Halt'], ['herringbone', 'Halt + experimental Herringbone']]
], [
  'red_range',
  'Red weapon range, all sites (m)',
  'number',
  0,
  5000,
  50,
  'Changing this applies to all Red sites; individual sites can override it in Inspector.'
], ['leader_loss', 'Leader-loss policy', 'select', [
  ['promote', 'Promote'],
  ['halt', 'Halt'],
  ['absorb', 'Absorb'],
  ['continue', 'Continue independently']
]], ['comms', 'Communications level', 'select', [
  [0, 'C0 · 0 step delay / 0% drop'],
  [1, 'C1 · 1 step / 5%'],
  [2, 'C2 · 2 steps / 10%'],
  [3, 'C3 · 4 steps / 20%'],
  [4, 'C4 · 8 steps / 35%'],
  [5, 'C5 · 16 steps / 55%']
]], ['duration', 'Mission horizon (s)', 'number', 10, 7200, 10], ['seed', 'Random seed', 'number', 0, 2147483647, 1], [
  'required_fraction',
  'Required cargo fraction',
  'number',
  .01,
  1,
  .05,
  '1 means 100% of the loaded cargo must arrive.'
]];

const advanced = [['control_crew', 'People / control', 'number', 1, 8, 1], [
  'cargo_crew',
  'People / crewed cargo truck',
  'number',
  0,
  8,
  1,
  'Supervised-autonomous mode assigns zero onboard cargo crew.'
], ['escort_crew', 'People / escort', 'number', 1, 8, 1], ['recovery_crew', 'People / recovery', 'number', 1, 8, 1], [
  'staging_m',
  'Staging lead offset (m)',
  'number',
  0,
  10000,
  50,
  'Lead starts this far along the route from the start-area marker. This stays fixed across comparison arms.'
], ['max_speed', 'Platform max speed (m/s)', 'number', .1, 30, .5], ['vehicle_length', 'Vehicle physical length (m)', 'number', 2, 20, .5], ['contact_clear_s', 'Contact clear interval (s)', 'number', 1, 3600, 1], ['handoff_steps', 'Promotion / absorb delay (steps)', 'number', 0, 600, 1], [
  'succession',
  'Eligible leader rule',
  'select',
  [['manned_only', 'Living crewed candidate only'], ['any', 'Any living candidate']]
], ['halt_max_s', 'Leader halt maximum (s; 0 = none)', 'number', 0, 3600, 1], [
  'halt_clear_steps',
  'Leader halt clear steps (0 = none)',
  'number',
  0,
  3600,
  1,
  'Range-only ground-truth clearance, not Blue detection.'
], ['console_transfer', 'Console ownership after loss', 'select', [
  ['fixed', 'Fixed original console (core)'],
  ['successor', 'Experimental transfer to promoted crewed head']
]], ['console_delay_s', 'Console transfer delay (s)', 'number', 0, 600, 1], ['span_capacity', 'Console span capacity', 'number', .1, 100, .5], ['service_rate', 'Console service rate (decisions/step)', 'number', .01, 10, .05], ['decision_interval', 'Periodic request interval (steps)', 'number', 1, 600, 1], ['patience', 'Request patience (steps)', 'number', 1, 600, 1], ['exceptions', 'Enable track-timeout exception requests', 'checkbox'], ['escort_range', 'Escort weapon range (m)', 'number', 0, 5000, 50], [
  'escort_pk',
  'Escort base damage probability',
  'number',
  0,
  1,
  .001,
  'Uncalibrated per-opportunity assumption.'
], ['herringbone_offset', 'Herringbone forward/lateral offset (m)', 'number', 5, 50, 1], [
  'target_priority',
  'Red target selection',
  'select',
  [['nearest', 'Nearest eligible (core)'], ['control_first', 'Control first (preserved #18 selector)']]
], [
  'diagnostic_loss_s',
  'Forced head-loss time (s; blank = off)',
  'optional',
  0,
  7199,
  1,
  'Diagnostic intervention only; default missions have no forced loss.'
], [
  'cell',
  'Map raster cell (m)',
  'number',
  5,
  100,
  5,
  'Smaller cells cost more time; buildings occupy their conservative raster footprint.'
]];

const factorNames = {
  pace: 'Commanded pace',
  time_gap: 'Time gap',
  min_gap: 'Minimum station gap',
  vehicles_per_unit: 'Core vehicles per unit',
  units_per_serial: 'Units per serial',
  serials: 'Serials',
  escorts: 'Additional escorts',
  payload_kg: 'Loaded payload per truck (kg)',
  response: 'Contact response',
  leader_loss: 'Leader-loss policy',
  comms: 'Communications level'
};

function notice(text, error = false) {
  $('notice').hidden = !text;
  $('notice').textContent = text;
  $('notice').classList.toggle('error', error);
}

function store() {
  try {
    localStorage.setItem('sandtable-v3-draft', JSON.stringify(draft));
  } catch {}
}

function checkpoint() {
  historyStack.push(clone(draft));

  if (historyStack.length > 30)
    historyStack.shift();
}
