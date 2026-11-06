'use strict';

// Edit one road's planning score. Routing and cost calculations stay in Python.
class RoadEditor {
  constructor(root, road, {onChange, onReplan, routeReady, routing}) {
    this.root = root;
    this.road = road;
    this.onChange = onChange;
    this.onReplan = onReplan;
    this.routeReady = routeReady;
    this.routing = routing;
  }

  render() {
    const road = this.road;
    const manual = (road.exposure_mode || 'manual') === 'manual';
    const estimate = road.exposure_auto;
    const used = manual ? road.exposure : estimate;
    const score = Number.isFinite(used) ? fmt(used * 100, 1) : '…';
    const edges = this.routing?.selected_edges || [];
    const path = edges.length ? [...edges.map(e => e.u), edges.at(-1).v].join(' → ') : '';
    this.root.innerHTML = `
      <h3 class="road-editor-title">${esc(road.u)} ↔ ${esc(road.v)}</h3>
      <p>Editing <b>${esc(road.id)}</b> · this road only</p>
      <form id="roadScoreForm" class="road-score-editor">
        <div class="road-score-summary">
          <span>Road exposure score</span>
          <strong><output id="roadScoreUsed">${score}</output><small> / 100</small></strong>
          <span>${manual ? 'Your custom score' : 'Calculated from the map'}</span>
        </div>
        <p>A higher score makes this road more costly for the route planner.</p>
        <div class="road-score-modes" role="group" aria-label="How to set this road's score">
          <button type="button" id="roadScoreAuto" aria-pressed="${!manual}">Use map estimate</button>
          <button type="button" id="roadScoreCustom" aria-pressed="${manual}">Set my score</button>
        </div>
        ${manual ? `
          <div class="road-custom-score">
            <label for="roadScoreValue">Your score (0–100)</label>
            <input id="roadScoreValue" type="number" min="0" max="100" step="any"
              value="${Number((road.exposure * 100).toFixed(4))}" required
              aria-describedby="roadScoreHelp">
            <input id="roadScoreSlider" type="range" min="0" max="100" step="0.1"
              value="${road.exposure * 100}" aria-label="Adjust this road's exposure score">
            <div class="road-score-ends"><span>0 · less exposure</span><span>100 · more exposure</span></div>
          </div>` : '<p>Uses declared Red positions, weapon ranges and building screening.</p>'}
        <p id="roadScoreHelp" class="road-score-help">Planning score, not a casualty percentage.
          Changes here affect route choice, not Red weapons.</p>
        <p id="roadScoreStatus" role="status">${this.routeReady
          ? 'The route reflects the current draft settings.'
          : 'Draft changed. Update the route to see its new cost.'}</p>
        <p id="roadChosenPath" class="road-chosen-path" ${this.routeReady ? '' : 'hidden'}>
          <b>Chosen path</b><br>${esc(path)}<br>Cost: ${fmt(this.routing?.cost || 0)}
        </p>
        <button type="submit" id="updateRoadRoute" class="primary wide">Update route using this score</button>
        <p class="road-score-help">Chooses a route automatically. Run the mission separately.</p>
        <details class="road-properties">
          <summary>Road width & movement</summary>
          <label>Width (m)<input type="number" data-road-property="width" min="8" max="300"
            step="any" value="${road.width}" required></label>
          <label>Road movement multiplier<input type="number" data-road-property="speed_mult"
            min="0.1" max="1" step="any" value="${road.speed_mult}" required></label>
          <small>1 = normal movement; smaller values slow movement on this road.</small>
        </details>
      </form>`;

    const find = id => this.root.querySelector('#' + id);
    find('roadScoreAuto').onclick = () => this.onChange({exposure_mode: 'auto'}, true);
    find('roadScoreCustom').onclick = () => this.onChange({
      exposure_mode: 'manual',
      exposure: manual ? road.exposure : (Number.isFinite(estimate) ? estimate : road.exposure)
    }, true);

    const markPending = () => {
      find('roadScoreStatus').textContent = 'Draft score saved. Update the route to see its new cost.';
      find('roadChosenPath').hidden = true;
    };
    if (manual) {
      const number = find('roadScoreValue');
      const slider = find('roadScoreSlider');
      const preview = score => {
        find('roadScoreUsed').textContent = fmt(score, 1);
        find('roadChosenPath').hidden = true;
        find('roadScoreStatus').textContent = 'Score changed. Update the route to compare paths.';
      };
      const save = score => {
        this.onChange({exposure_mode: 'manual', exposure: score / 100}, false);
        markPending();
      };
      number.oninput = () => {
        if (number.validity.valid) {
          slider.value = number.value;
          preview(number.valueAsNumber);
        }
      };
      number.onchange = () => {
        if (number.reportValidity()) save(number.valueAsNumber);
      };
      slider.oninput = () => {
        number.value = slider.value;
        preview(Number(slider.value));
      };
      slider.onchange = () => save(Number(slider.value));
    }
    this.root.querySelectorAll('[data-road-property]').forEach(input => {
      input.onchange = () => {
        if (!input.reportValidity()) return;
        this.onChange({[input.dataset.roadProperty]: input.valueAsNumber}, false);
        markPending();
      };
    });
    find('roadScoreForm').onsubmit = async event => {
      event.preventDefault();
      if (!find('roadScoreForm').reportValidity()) return;
      const button = find('updateRoadRoute');
      button.disabled = true;
      button.textContent = 'Updating route…';
      await this.onReplan();
    };
  }
}
