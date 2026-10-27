#!/usr/bin/env python3
"""Run the Issue #15 Convoy Separation Parameter LHS sweep and generate an interactive HTML dashboard.

Corresponds to `studies/uc3_convoy_sweep.yaml`:
  - 32 Latin Hypercube sample points + 1 baseline reference point
  - Parameters: pace (6-14 m/s), time_gap (2-8 s), element_time_gap (10-40 s),
    march_unit_size (3-7 int), security_ratio (0.0-0.5)
  - Metrics: success_rate, blue_losses, blue_loss_frac, time_to_objective,
    convoy_column_length, convoy_road_space, convoy_pass_time, convoy_road_clearance_time,
    and multi-objective MissionScoreMetric cost J.

Outputs:
  report/viz/convoy_sweep_data.json
  report/viz/convoy_results.html
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import scipy.stats.qmc as qmc

from sandtable.scenario import load_scenario
from sandtable.sim import run_mission

SEEDS_PER_SAMPLE = 5
N_SAMPLES = 32

PARAM_BOUNDS = {
    "pace": (6.0, 14.0),
    "time_gap": (2.0, 8.0),
    "element_time_gap": (10.0, 40.0),
    "march_unit_size": (3, 7),  # integer
    "security_ratio": (0.0, 0.5),
}


def generate_samples(n: int = 32, seed: int = 42) -> list[dict]:
    sampler = qmc.LatinHypercube(d=5, seed=seed)
    unit_samples = sampler.random(n=n)

    samples = []
    # Index 0: Doctrinal Baseline Reference
    samples.append({
        "id": "REF-BASE",
        "name": "Registered Baseline",
        "pace": 10.0,
        "time_gap": 4.0,
        "element_time_gap": 20.0,
        "march_unit_size": 5,
        "security_ratio": 0.33,
        "is_baseline": True,
    })

    for i in range(n):
        u = unit_samples[i]
        p_pace = round(float(PARAM_BOUNDS["pace"][0] + u[0] * (PARAM_BOUNDS["pace"][1] - PARAM_BOUNDS["pace"][0])), 2)
        p_gap = round(float(PARAM_BOUNDS["time_gap"][0] + u[1] * (PARAM_BOUNDS["time_gap"][1] - PARAM_BOUNDS["time_gap"][0])), 2)
        p_egap = round(float(PARAM_BOUNDS["element_time_gap"][0] + u[2] * (PARAM_BOUNDS["element_time_gap"][1] - PARAM_BOUNDS["element_time_gap"][0])), 1)
        p_musize = int(round(PARAM_BOUNDS["march_unit_size"][0] + u[3] * (PARAM_BOUNDS["march_unit_size"][1] - PARAM_BOUNDS["march_unit_size"][0])))
        p_sec = round(float(PARAM_BOUNDS["security_ratio"][0] + u[4] * (PARAM_BOUNDS["security_ratio"][1] - PARAM_BOUNDS["security_ratio"][0])), 2)

        samples.append({
            "id": f"LHS-{i+1:02d}",
            "name": f"Config #{i+1}",
            "pace": p_pace,
            "time_gap": p_gap,
            "element_time_gap": p_egap,
            "march_unit_size": p_musize,
            "security_ratio": p_sec,
            "is_baseline": False,
        })
    return samples


def evaluate_sample(scn, sample: dict) -> dict:
    params = {
        "pace": sample["pace"],
        "time_gap": sample["time_gap"],
        "element_time_gap": sample["element_time_gap"],
        "march_unit_size": sample["march_unit_size"],
        "security_ratio": sample["security_ratio"],
    }
    runs = [run_mission(scn, seed=s, params=params) for s in range(SEEDS_PER_SAMPLE)]

    succ_rate = float(np.mean([r["success"] for r in runs]))
    b_loss = float(np.mean([r["blue_losses"] for r in runs]))
    b_loss_frac = float(np.mean([r["blue_loss_frac"] for r in runs]))
    r_loss = float(np.mean([r["red_losses"] for r in runs]))
    t_obj = float(np.mean([r["time_to_objective"] for r in runs]))

    # Convoy doctrine metrics
    cl = float(runs[0].get("convoy_column_length", 0.0))
    rs = float(runs[0].get("convoy_road_space", 0.0))
    pt = float(runs[0].get("convoy_pass_time", 0.0))
    rct = float(runs[0].get("convoy_road_clearance_time", 0.0))
    vm = float(runs[0].get("convoy_rate_of_march", sample["pace"]))

    # Composite MissionScoreMetric J: w_fail=1.0, w_time=0.3, w_loss=0.5, w_road=0.2
    # J = 1.0*(1 - succ) + 0.3*(t_obj/1800) + 0.5*b_loss_frac + 0.2*(rs/2000)
    score = (
        1.0 * (1.0 - succ_rate)
        + 0.3 * (t_obj / 1800.0)
        + 0.5 * b_loss_frac
        + 0.2 * (rs / 2000.0)
    )

    total_veh = sample["march_unit_size"] * 3 * 1

    return {
        **sample,
        "total_vehicles": total_veh,
        "success_rate": round(succ_rate, 2),
        "blue_losses": round(b_loss, 2),
        "blue_loss_frac": round(b_loss_frac, 3),
        "red_losses": round(r_loss, 2),
        "time_to_objective": round(t_obj, 1),
        "column_length": round(cl, 1),
        "road_space": round(rs, 1),
        "pass_time": round(pt, 1),
        "road_clearance_time": round(rct, 1),
        "rate_of_march": round(vm, 1),
        "mission_score": round(score, 3),
    }


def find_pareto_front(results: list[dict]) -> list[bool]:
    """Identify Pareto optimal solutions minimizing both Road Space and Blue Loss Frac."""
    is_pareto = []
    for i, a in enumerate(results):
        dominated = False
        for j, b in enumerate(results):
            if i == j:
                continue
            # b dominates a if b is <= in both and < in at least one
            if (b["road_space"] <= a["road_space"] and b["blue_loss_frac"] <= a["blue_loss_frac"]) and (
                b["road_space"] < a["road_space"] or b["blue_loss_frac"] < a["blue_loss_frac"]
            ):
                dominated = True
                break
        is_pareto.append(not dominated)
    return is_pareto


def main():
    print("Loading uc3_convoy scenario...")
    scn = load_scenario("scenarios/uc3_convoy.json")

    print(f"Generating {N_SAMPLES} Latin Hypercube samples (+ 1 baseline reference)...")
    samples = generate_samples(N_SAMPLES, seed=42)

    print(f"Evaluating {len(samples)} configurations across {SEEDS_PER_SAMPLE} seeds each...")
    results = []
    for idx, s in enumerate(samples):
        res = evaluate_sample(scn, s)
        results.append(res)
        print(f"  [{res['id']}] pace={res['pace']:4.1f}m/s gap={res['time_gap']:3.1f}s sec={res['security_ratio']:.2f} | "
              f"RS={res['road_space']:6.1f}m bLoss={res['blue_losses']:4.1f} succ={res['success_rate']*100:3.0f}% score={res['mission_score']:.3f}")

    # Mark Pareto frontier
    pareto_mask = find_pareto_front(results)
    for i, p in enumerate(pareto_mask):
        results[i]["is_pareto"] = bool(p)

    out_dir = Path("report/viz")
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "convoy_sweep_data.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nWrote sweep data to {json_path}")

    html_path = out_dir / "convoy_results.html"
    html_content = generate_html(results)
    html_path.write_text(html_content)
    print(f"Wrote interactive dashboard to {html_path} ({len(html_content)/1024:.1f} KB)")


def generate_html(results: list[dict]) -> str:
    payload_json = json.dumps(results)
    best_score = min(r["mission_score"] for r in results)
    best_config = next(r for r in results if r["mission_score"] == best_score)
    min_rs = min(r["road_space"] for r in results)
    max_succ = max(r["success_rate"] for r in results)
    pareto_count = sum(1 for r in results if r["is_pareto"])

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SandTable - Convoy Separation Search Results</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #090d12;
    --panel: #111721;
    --panel-sub: #161e2a;
    --panel-border: #232f3e;
    --ink: #e2e8f0;
    --ink-dim: #94a3b8;
    --ink-faint: #64748b;
    --blue: #3b82f6;
    --cyan: #06b6d4;
    --amber: #f59e0b;
    --emerald: #10b981;
    --rose: #f43f5e;
    --purple: #a855f7;
    --gold: #fbbf24;
    --font-sans: 'Inter', system-ui, -apple-system, sans-serif;
    --font-mono: 'JetBrains Mono', ui-monospace, Menlo, monospace;
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: var(--bg);
    color: var(--ink);
    font-family: var(--font-sans);
    line-height: 1.5;
    padding: 24px;
    min-height: 100vh;
  }}

  .container {{
    max-width: 1400px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }}

  /* Top Navigation Bar */
  header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--panel-border);
    flex-wrap: wrap;
    gap: 16px;
  }}
  .brand {{
    display: flex;
    align-items: center;
    gap: 12px;
  }}
  .badge-tag {{
    background: rgba(245, 158, 11, 0.15);
    color: var(--amber);
    border: 1px solid rgba(245, 158, 11, 0.35);
    font-family: var(--font-mono);
    font-size: 11px;
    padding: 3px 8px;
    border-radius: 4px;
    font-weight: 600;
    text-transform: uppercase;
  }}
  h1 {{
    font-size: 19px;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #fff;
  }}
  .nav-links {{
    display: flex;
    gap: 10px;
  }}
  .btn-link {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: var(--panel);
    border: 1px solid var(--panel-border);
    color: var(--ink);
    text-decoration: none;
    padding: 7px 12px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    transition: all 0.15s ease;
  }}
  .btn-link:hover {{
    background: var(--panel-sub);
    border-color: var(--amber);
    color: #fff;
  }}
  .btn-link.primary {{
    background: rgba(245, 158, 11, 0.15);
    border-color: var(--amber);
    color: var(--amber);
  }}

  /* KPI Summary Grid */
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 14px;
  }}
  .kpi-card {{
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: 10px;
    padding: 16px 18px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }}
  .kpi-title {{
    font-size: 12px;
    color: var(--ink-faint);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
  }}
  .kpi-val {{
    font-family: var(--font-mono);
    font-size: 24px;
    font-weight: 700;
    color: #fff;
    display: flex;
    align-items: baseline;
    gap: 6px;
  }}
  .kpi-sub {{
    font-size: 12px;
    color: var(--ink-dim);
  }}

  /* Charts Grid */
  .charts-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }}
  @media (max-width: 1024px) {{
    .charts-grid {{ grid-template-columns: 1fr; }}
  }}
  .chart-card {{
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: 10px;
    padding: 18px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    position: relative;
  }}
  .chart-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .chart-title {{
    font-size: 14px;
    font-weight: 600;
    color: #fff;
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .chart-sub {{
    font-size: 12px;
    color: var(--ink-dim);
  }}
  .chart-wrapper {{
    position: relative;
    width: 100%;
    height: 320px;
  }}
  canvas.chart-cv {{
    display: block;
    width: 100%;
    height: 100%;
  }}
  .tooltip {{
    position: absolute;
    display: none;
    background: rgba(15, 23, 42, 0.95);
    border: 1px solid var(--panel-border);
    padding: 8px 12px;
    border-radius: 6px;
    font-family: var(--font-mono);
    font-size: 11.5px;
    color: var(--ink);
    pointer-events: none;
    z-index: 100;
    box-shadow: 0 4px 12px rgba(0,0,0,0.5);
  }}

  /* Table Section */
  .table-card {{
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: 10px;
    padding: 18px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }}
  .table-controls {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }}
  .search-box {{
    background: var(--panel-sub);
    border: 1px solid var(--panel-border);
    border-radius: 6px;
    padding: 7px 12px;
    font-family: var(--font-sans);
    font-size: 13px;
    color: var(--ink);
    min-width: 280px;
  }}
  .search-box:focus {{
    outline: 2px solid var(--amber);
    border-color: var(--amber);
  }}
  .table-wrapper {{
    overflow-x: auto;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-family: var(--font-mono);
    font-size: 12.5px;
  }}
  th, td {{
    padding: 10px 14px;
    text-align: right;
    border-bottom: 1px solid var(--panel-border);
  }}
  th:first-child, td:first-child, th:nth-child(2), td:nth-child(2) {{
    text-align: left;
  }}
  th {{
    background: var(--panel-sub);
    color: var(--ink-faint);
    font-weight: 600;
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 0.05em;
    cursor: pointer;
    user-select: none;
  }}
  th:hover {{
    color: var(--amber);
  }}
  tr:hover td {{
    background: rgba(255, 255, 255, 0.02);
  }}
  tr.is-baseline td {{
    background: rgba(59, 130, 246, 0.07);
    border-left: 2px solid var(--blue);
  }}
  tr.is-pareto td {{
    color: #fff;
  }}
  .tag-pareto {{
    background: rgba(16, 185, 129, 0.15);
    color: var(--emerald);
    border: 1px solid rgba(16, 185, 129, 0.3);
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 600;
  }}
  .tag-ref {{
    background: rgba(59, 130, 246, 0.15);
    color: var(--blue);
    border: 1px solid rgba(59, 130, 246, 0.3);
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 600;
  }}
</style>
</head>
<body>

<div class="container">
  <header>
    <div class="brand">
      <h1>Convoy Separation Search Dashboard</h1>
      <span class="badge-tag">Issue #15 &middot; ATP 4-11 &amp; ATP 4-16</span>
    </div>
    <div class="nav-links">
      <a href="mission_viewer.html" class="btn-link primary">
        <span>&#9654; Tactical Mission Replay Console</span>
      </a>
      <a href="player.html" class="btn-link">
        <span>Lightweight Player</span>
      </a>
      <button id="exportBtn" class="btn-link" onclick="downloadJSON()">
        <span>&#8681; Export JSON</span>
      </button>
    </div>
  </header>

  <!-- KPI Summaries -->
  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-title">Total Swept Configurations</div>
      <div class="kpi-val">{len(results)} <span style="font-size:13px;color:var(--ink-dim);font-weight:400">runs</span></div>
      <div class="kpi-sub">32 LHS points + 1 Doctrinal Baseline</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Best Mission Cost J</div>
      <div class="kpi-val" style="color:var(--emerald)">{best_score:.3f}</div>
      <div class="kpi-sub">Config <b>{best_config['id']}</b> (RS={best_config['road_space']:.0f}m, bLoss={best_config['blue_losses']:.1f})</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Pareto Optimal Frontier</div>
      <div class="kpi-val" style="color:var(--amber)">{pareto_count} <span style="font-size:13px;color:var(--ink-dim);font-weight:400">solutions</span></div>
      <div class="kpi-sub">Minimizing Road Space vs. Attrition</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Min Road Space (RS)</div>
      <div class="kpi-val">{min_rs:.0f} <span style="font-size:13px;color:var(--ink-dim);font-weight:400">m</span></div>
      <div class="kpi-sub">Max Road Space: {max(r['road_space'] for r in results):.0f} m</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Peak Survival Rate</div>
      <div class="kpi-val" style="color:var(--cyan)">{max_succ*100:.0f}%</div>
      <div class="kpi-sub">Evaluated over {SEEDS_PER_SAMPLE} seeds/sample</div>
    </div>
  </div>

  <!-- Interactive Charts Grid -->
  <div class="charts-grid">
    <!-- Chart 1: Doctrinal Tradeoff (Road Space vs Blue Losses) -->
    <div class="chart-card">
      <div class="chart-header">
        <div>
          <div class="chart-title">
            <span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:var(--amber)"></span>
            ATP 4-11 (G-9) Doctrinal Tradeoff: Road Space vs. Losses
          </div>
          <div class="chart-sub">Tension between vulnerable road occupancy and dispersion against ambush fires</div>
        </div>
      </div>
      <div class="chart-wrapper">
        <canvas id="chart1" class="chart-cv"></canvas>
        <div id="tip1" class="tooltip"></div>
      </div>
    </div>

    <!-- Chart 2: Security Ratio vs Ambush Loss -->
    <div class="chart-card">
      <div class="chart-header">
        <div>
          <div class="chart-title">
            <span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:var(--cyan)"></span>
            Security Escort Ratio vs. Blue Convoy Losses
          </div>
          <div class="chart-sub">Gun truck escort density impact on suppression of enemy ambushes</div>
        </div>
      </div>
      <div class="chart-wrapper">
        <canvas id="chart2" class="chart-cv"></canvas>
        <div id="tip2" class="tooltip"></div>
      </div>
    </div>

    <!-- Chart 3: Pass Time vs Pace & Time Gap -->
    <div class="chart-card">
      <div class="chart-header">
        <div>
          <div class="chart-title">
            <span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:var(--purple)"></span>
            Pass Time (PT) vs. March Pace
          </div>
          <div class="chart-sub">ATP 4-16 relationship: PT = CL / v_march across time gap levels</div>
        </div>
      </div>
      <div class="chart-wrapper">
        <canvas id="chart3" class="chart-cv"></canvas>
        <div id="tip3" class="tooltip"></div>
      </div>
    </div>

    <!-- Chart 4: Mission Score Cost Distribution -->
    <div class="chart-card">
      <div class="chart-header">
        <div>
          <div class="chart-title">
            <span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:var(--emerald)"></span>
            Multi-Objective Cost J vs. Road Space
          </div>
          <div class="chart-sub">Scalarized objective J (Losses + Time + Road Space Penalty w_road=0.2)</div>
        </div>
      </div>
      <div class="chart-wrapper">
        <canvas id="chart4" class="chart-cv"></canvas>
        <div id="tip4" class="tooltip"></div>
      </div>
    </div>
  </div>

  <!-- Interactive Data Table -->
  <div class="table-card">
    <div class="table-controls">
      <div style="font-weight:600;font-size:15px;color:#fff;">
        All Evaluated Convoy Configurations ({len(results)})
      </div>
      <input type="text" id="filterInput" class="search-box" placeholder="Filter by ID, pace, unit size, or tag..." oninput="filterTable()">
    </div>
    <div class="table-wrapper">
      <table id="resultsTable">
        <thead>
          <tr>
            <th onclick="sortTable(0)">ID</th>
            <th onclick="sortTable(1)">Type</th>
            <th onclick="sortTable(2)">Pace (m/s)</th>
            <th onclick="sortTable(3)">Time Gap (s)</th>
            <th onclick="sortTable(4)">Elem Gap (s)</th>
            <th onclick="sortTable(5)">Veh / Unit</th>
            <th onclick="sortTable(6)">Sec Ratio</th>
            <th onclick="sortTable(7)">Road Space (m)</th>
            <th onclick="sortTable(8)">Pass Time (s)</th>
            <th onclick="sortTable(9)">Blue Loss</th>
            <th onclick="sortTable(10)">Success</th>
            <th onclick="sortTable(11)">Cost J</th>
          </tr>
        </thead>
        <tbody id="tableBody">
          <!-- Populated by JS -->
        </tbody>
      </table>
    </div>
  </div>
</div>

<script>
const DATA = {payload_json};

function renderTable(rows) {{
  const tbody = document.getElementById("tableBody");
  tbody.innerHTML = rows.map(r => `
    <tr class="${{r.is_baseline ? 'is-baseline' : ''}} ${{r.is_pareto ? 'is-pareto' : ''}}">
      <td><b>${{r.id}}</b></td>
      <td>
        ${{r.is_baseline ? '<span class="tag-ref">BASELINE</span>' : ''}}
        ${{r.is_pareto ? '<span class="tag-pareto">PARETO</span>' : ''}}
      </td>
      <td>${{r.pace.toFixed(1)}}</td>
      <td>${{r.time_gap.toFixed(1)}}</td>
      <td>${{r.element_time_gap.toFixed(1)}}</td>
      <td>${{r.march_unit_size}}</td>
      <td>${{r.security_ratio.toFixed(2)}}</td>
      <td><b>${{r.road_space.toFixed(0)}}</b></td>
      <td>${{r.pass_time.toFixed(1)}}</td>
      <td style="color:${{r.blue_losses > 3.0 ? 'var(--rose)' : 'var(--ink)'}}">${{r.blue_losses.toFixed(1)}}</td>
      <td style="color:${{r.success_rate >= 0.8 ? 'var(--emerald)' : (r.success_rate < 0.4 ? 'var(--rose)' : 'var(--amber)')}}">
        ${{(r.success_rate * 100).toFixed(0)}}%
      </td>
      <td style="font-weight:700;color:${{r.mission_score < 0.35 ? 'var(--emerald)' : 'var(--ink)'}}">${{r.mission_score.toFixed(3)}}</td>
    </tr>
  `).join("");
}}

let currentData = [...DATA];
renderTable(currentData);

function filterTable() {{
  const q = document.getElementById("filterInput").value.toLowerCase();
  currentData = DATA.filter(r =>
    r.id.toLowerCase().includes(q) ||
    r.name.toLowerCase().includes(q) ||
    (r.is_pareto && "pareto".includes(q)) ||
    (r.is_baseline && "baseline".includes(q)) ||
    String(r.pace).includes(q) ||
    String(r.march_unit_size).includes(q)
  );
  renderTable(currentData);
}}

let sortDir = 1, lastCol = -1;
function sortTable(col) {{
  if (lastCol === col) sortDir = -sortDir;
  else {{ sortDir = 1; lastCol = col; }}

  const keys = [
    "id", "is_baseline", "pace", "time_gap", "element_time_gap",
    "march_unit_size", "security_ratio", "road_space", "pass_time",
    "blue_losses", "success_rate", "mission_score"
  ];
  const key = keys[col];
  currentData.sort((a, b) => {{
    let va = a[key], vb = b[key];
    if (typeof va === "string") return sortDir * va.localeCompare(vb);
    return sortDir * (va - vb);
  }});
  renderTable(currentData);
}}

function downloadJSON() {{
  const blob = new Blob([JSON.stringify(DATA, null, 2)], {{type: "application/json"}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "convoy_sweep_results.json";
  a.click();
  URL.revokeObjectURL(url);
}}

// ---- Chart Drawing Engine ----
function setupScatter(canvasId, tipId, xKey, yKey, xLabel, yLabel, formatX, formatY, colorFn) {{
  const cv = document.getElementById(canvasId);
  const tip = document.getElementById(tipId);
  const ctx = cv.getContext("2d");

  function draw() {{
    const rect = cv.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    cv.width = rect.width * dpr;
    cv.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const W = rect.width, H = rect.height;
    const pad = {{ l: 54, r: 24, t: 20, b: 40 }};
    const pw = W - pad.l - pad.r;
    const ph = H - pad.t - pad.b;

    ctx.clearRect(0, 0, W, H);

    // Ranges
    const xs = DATA.map(d => d[xKey]);
    const ys = DATA.map(d => d[yKey]);
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    const spanX = (maxX - minX) || 1;
    const spanY = (maxY - minY) || 1;

    // Grid lines
    ctx.strokeStyle = "#1b2532";
    ctx.lineWidth = 1;
    ctx.font = "10px JetBrains Mono, monospace";
    ctx.fillStyle = "#64748b";

    for (let i = 0; i <= 4; i++) {{
      const gy = pad.t + ph * (i / 4);
      ctx.beginPath();
      ctx.moveTo(pad.l, gy);
      ctx.lineTo(pad.l + pw, gy);
      ctx.stroke();
      const valY = maxY - (i / 4) * spanY;
      ctx.textAlign = "right";
      ctx.fillText(formatY(valY), pad.l - 8, gy + 3);

      const gx = pad.l + pw * (i / 4);
      ctx.beginPath();
      ctx.moveTo(gx, pad.t);
      ctx.lineTo(gx, pad.t + ph);
      ctx.stroke();
      const valX = minX + (i / 4) * spanX;
      ctx.textAlign = "center";
      ctx.fillText(formatX(valX), gx, H - pad.b + 18);
    }}

    // Axis labels
    ctx.fillStyle = "#94a3b8";
    ctx.font = "11px Inter, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(xLabel, pad.l + pw / 2, H - 8);

    ctx.save();
    ctx.translate(14, pad.t + ph / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText(yLabel, 0, 0);
    ctx.restore();

    // If pareto front available in Chart 1, draw frontier line
    if (xKey === "road_space" && yKey === "blue_losses") {{
      const paretoPts = DATA.filter(d => d.is_pareto)
        .sort((a,b) => a.road_space - b.road_space);
      if (paretoPts.length > 1) {{
        ctx.strokeStyle = "rgba(245, 158, 11, 0.4)";
        ctx.lineWidth = 2;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        paretoPts.forEach((pt, idx) => {{
          const px = pad.l + ((pt.road_space - minX) / spanX) * pw;
          const py = pad.t + ph - ((pt.blue_losses - minY) / spanY) * ph;
          if (idx === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        }});
        ctx.stroke();
        ctx.setLineDash([]);
      }}
    }}

    // Draw Points
    DATA.forEach(d => {{
      const px = pad.l + ((d[xKey] - minX) / spanX) * pw;
      const py = pad.t + ph - ((d[yKey] - minY) / spanY) * ph;

      ctx.beginPath();
      const rad = d.is_baseline ? 7 : (d.is_pareto ? 6 : 4.5);
      ctx.arc(px, py, rad, 0, Math.PI * 2);

      const col = colorFn(d);
      ctx.fillStyle = col;
      ctx.fill();

      if (d.is_baseline) {{
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2;
        ctx.stroke();
      }} else if (d.is_pareto) {{
        ctx.strokeStyle = "#f59e0b";
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }}
    }});
  }}

  draw();
  window.addEventListener("resize", draw);

  // Mouse hover tooltip
  cv.addEventListener("mousemove", e => {{
    const rect = cv.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    const pad = {{ l: 54, r: 24, t: 20, b: 40 }};
    const pw = rect.width - pad.l - pad.r;
    const ph = rect.height - pad.t - pad.b;

    const xs = DATA.map(d => d[xKey]);
    const ys = DATA.map(d => d[yKey]);
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    const spanX = (maxX - minX) || 1;
    const spanY = (maxY - minY) || 1;

    let hit = null, minDist = 12;
    DATA.forEach(d => {{
      const px = pad.l + ((d[xKey] - minX) / spanX) * pw;
      const py = pad.t + ph - ((d[yKey] - minY) / spanY) * ph;
      const dist = Math.hypot(mx - px, my - py);
      if (dist < minDist) {{
        minDist = dist;
        hit = d;
      }}
    }});

    if (hit) {{
      tip.style.display = "block";
      tip.style.left = (mx + 15) + "px";
      tip.style.top = (my - 10) + "px";
      tip.innerHTML = `
        <div style="font-weight:700;color:#fff;margin-bottom:3px">${{hit.id}} ${{hit.is_baseline?'(Baseline)':''}}</div>
        <div>Pace: <b>${{hit.pace}} m/s</b> &middot; Gap: <b>${{hit.time_gap}}s</b></div>
        <div>Veh/Unit: <b>${{hit.march_unit_size}}</b> &middot; Sec: <b>${{hit.security_ratio}}</b></div>
        <div style="border-top:1px solid #334155;margin-top:4px;padding-top:4px">
          RS: <b>${{hit.road_space.toFixed(0)}} m</b> &middot; Loss: <b>${{hit.blue_losses.toFixed(1)}}</b>
        </div>
        <div>Cost J: <b style="color:var(--emerald)">${{hit.mission_score.toFixed(3)}}</b></div>
      `;
    }} else {{
      tip.style.display = "none";
    }}
  }});

  cv.addEventListener("mouseleave", () => {{ tip.style.display = "none"; }});
}}

// Initialize 4 interactive charts
setupScatter(
  "chart1", "tip1",
  "road_space", "blue_losses",
  "Road Space RS (meters) -- Vulnerability Footprint", "Blue Vehicle Losses (count)",
  v => Math.round(v) + "m", v => v.toFixed(1),
  d => d.is_baseline ? "#3b82f6" : (d.is_pareto ? "#f59e0b" : "rgba(148, 163, 184, 0.6)")
);

setupScatter(
  "chart2", "tip2",
  "security_ratio", "blue_losses",
  "Gun Truck Escort Ratio (security_ratio)", "Blue Losses (count)",
  v => v.toFixed(2), v => v.toFixed(1),
  d => d.security_ratio >= 0.33 ? "#06b6d4" : "#f43f5e"
);

setupScatter(
  "chart3", "tip3",
  "pace", "pass_time",
  "March Pace (m/s)", "Pass Time PT (seconds)",
  v => v.toFixed(1) + "m/s", v => Math.round(v) + "s",
  d => d.time_gap > 5.0 ? "#a855f7" : "#3b82f6"
);

setupScatter(
  "chart4", "tip4",
  "road_space", "mission_score",
  "Road Space RS (meters)", "Mission Score Objective J (Cost)",
  v => Math.round(v) + "m", v => v.toFixed(2),
  d => d.mission_score < 0.35 ? "#10b981" : (d.mission_score > 0.6 ? "#f43f5e" : "#f59e0b")
);
</script>
</body>
</html>
"""
    return html


if __name__ == "__main__":
    main()
