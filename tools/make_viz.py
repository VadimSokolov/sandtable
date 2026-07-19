"""Generate the self-contained mission-replay console (HTML) from recorded traces.

Records one representative run per curated scenario contrast (via ``sandtable.replay.record_trace``, which
replays ``run_mission`` step-for-step), subsamples frames to keep the payload light, embeds them in a
standalone HTML viewer, and writes two files:

  report/viz/mission_viewer.html   standalone document (open directly in a browser)
  report/viz/_artifact_body.html   body-only fragment (published via the Artifact tool)

Run:  PYTHONPATH=src python tools/make_viz.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from sandtable.replay import record_trace
from sandtable.scenario import load_scenario
from sandtable.sim import run_mission

REP_SEEDS = 25         # seeds scanned to characterize each contrast and pick a representative run
RECORD_STRIDE = 5      # sim steps between recorded snapshots
MAX_FRAMES = 90        # cap frames per trace (subsample beyond this)

# Curated contrasts: each row is the sensitive result of one scenario, shown as a before/after the
# viewer can flip between. (group, label, scenario, params).
SPECS = [
    ("UC-3  Route vs defilade",
     "Aggressive route (cover weight 0.15)", "scenarios/uc3_route_defilade.json",
     {"route_bias": 0.15}),
    ("UC-3  Route vs defilade",
     "Balanced route (0.50)", "scenarios/uc3_route_defilade.json",
     {"route_bias": 0.50}),
    ("UC-3  Route vs defilade",
     "Defilade route (cover weight 0.85)", "scenarios/uc3_route_defilade.json",
     {"route_bias": 0.85}),

    ("Span-of-control x comms  (centerpiece)",
     "Direct control, clear comms (C0, 1:8)", "scenarios/sc_span_control.json",
     {"control_mode": "direct", "comms_level": 0, "n_blue": 8}),
    ("Span-of-control x comms  (centerpiece)",
     "Direct control, jammed (C5, 1:8)", "scenarios/sc_span_control.json",
     {"control_mode": "direct", "comms_level": 5, "n_blue": 8}),
    ("Span-of-control x comms  (centerpiece)",
     "Supervisory autonomy, jammed (C5, 1:8)", "scenarios/sc_span_control.json",
     {"control_mode": "supervisory", "comms_level": 5, "n_blue": 8}),

    ("UC-5  Sensor swarm under EW",
     "No swarm (0 UAS)", "scenarios/uc5_sensor_swarm.json",
     {"n_uas": 0, "comms_level": 0}),
    ("UC-5  Sensor swarm under EW",
     "Swarm, clear comms (6 UAS, C0)", "scenarios/uc5_sensor_swarm.json",
     {"n_uas": 6, "comms_level": 0}),
    ("UC-5  Sensor swarm under EW",
     "Swarm, jammed relay (6 UAS, C5)", "scenarios/uc5_sensor_swarm.json",
     {"n_uas": 6, "comms_level": 5}),
]


def _subsample(frames: list, cap: int) -> list:
    """Keep at most `cap` frames, evenly spaced, always retaining the first and last."""
    if len(frames) <= cap:
        return frames
    step = (len(frames) - 1) / (cap - 1)
    idx = sorted({round(i * step) for i in range(cap)} | {0, len(frames) - 1})
    return [frames[i] for i in idx]


# Outcome fields used both to summarize a contrast and to pick its representative run.
_FIELDS = ("success", "blue_losses", "red_losses", "detection_coverage")


def pick_representative(scn, params: dict) -> tuple:
    """Scan REP_SEEDS runs; return (best_seed, aggregate) where best_seed is the run nearest the
    multi-seed mean outcome (z-scored across the four fields). This makes the displayed replay a
    TYPICAL run, not an outlier that could contradict the aggregate sweep, while `aggregate` records
    the honest multi-seed summary shown alongside it."""
    runs = [run_mission(scn, seed=s, params=params) for s in range(REP_SEEDS)]
    M = np.array([[r[f] for f in _FIELDS] for r in runs], float)
    mean = M.mean(0)
    std = M.std(0)
    std[std == 0] = 1.0
    dist = np.sqrt((((M - mean) / std) ** 2).sum(1))
    best = int(np.argmin(dist))
    agg = {
        "n": REP_SEEDS,
        "success_rate": float(np.mean([r["success"] for r in runs])),
        "blue_losses": float(mean[1]),
        "red_losses": float(mean[2]),
        "detection_coverage": float(mean[3]),
    }
    return best, agg


def build_traces() -> list:
    traces = []
    for group, label, path, params in SPECS:
        scn = load_scenario(path)
        seed, agg = pick_representative(scn, params)
        tr = record_trace(scn, seed=seed, params=params, stride=RECORD_STRIDE)
        tr["group"] = group
        tr["label"] = label
        tr["seed"] = seed
        tr["aggregate"] = agg
        tr["frames"] = _subsample(tr["frames"], MAX_FRAMES)
        traces.append(tr)
        oc = tr["outcome"]
        print(f"  {label:44s} seed={seed:2d} frames={len(tr['frames']):3d} | "
              f"run: succ={oc['success']:.0f} bL={oc['blue_losses']:.0f} rL={oc['red_losses']:.0f} "
              f"cov={oc['detection_coverage']:.2f} | "
              f"{REP_SEEDS}-seed: P(succ)={agg['success_rate']:.0%} "
              f"bL={agg['blue_losses']:.1f} cov={agg['detection_coverage']:.2f}")
    return traces


def main() -> None:
    print("Recording representative traces (scanning %d seeds each):" % REP_SEEDS)
    traces = build_traces()
    payload = json.dumps(traces, separators=(",", ":"))
    inner = TEMPLATE.replace("/*__TRACES__*/", payload)

    out_dir = Path("report/viz")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "_artifact_body.html").write_text(inner)
    standalone = (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
        "<title>SandTable Mission Replay</title>\n</head>\n<body>\n"
        + inner + "\n</body>\n</html>\n"
    )
    (out_dir / "mission_viewer.html").write_text(standalone)
    kb = len(standalone) / 1024
    print(f"\nWrote {out_dir/'mission_viewer.html'}  ({kb:.0f} KB)")
    print(f"Wrote {out_dir/'_artifact_body.html'}  (Artifact body fragment)")


# The viewer (style + markup + script). Data is injected at /*__TRACES__*/.
TEMPLATE = r"""<style>
  #stapp {
    --bg:#0a0e13; --panel:#121a23; --panel2:#0e151d; --edge:#22303d;
    --ink:#cdd8e3; --ink-dim:#7c8b9a; --ink-faint:#526170;
    --blue:#4fb0ff; --air:#37e6cf; --red:#ff5a72; --amber:#ffb03a; --good:#57d98a;
    --mono:"SFMono-Regular",ui-monospace,"JetBrains Mono",Menlo,Consolas,monospace;
    --sans:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
    background:var(--bg); color:var(--ink); font-family:var(--sans);
    min-height:100vh; box-sizing:border-box; padding:16px;
    display:flex; flex-direction:column; gap:12px;
  }
  #stapp *{box-sizing:border-box}
  #stapp .head{display:flex; align-items:baseline; gap:14px; flex-wrap:wrap;
    border-bottom:1px solid var(--edge); padding-bottom:10px}
  #stapp .brand{font-weight:700; letter-spacing:.14em; font-size:13px; text-transform:uppercase}
  #stapp .brand b{color:var(--amber)}
  #stapp .sub{color:var(--ink-dim); font-size:12px; letter-spacing:.02em}
  #stapp .sub .mono{font-family:var(--mono)}
  #stapp select{background:var(--panel2); color:var(--ink); border:1px solid var(--edge);
    border-radius:6px; padding:7px 10px; font-family:var(--mono); font-size:12.5px; min-width:340px}
  #stapp select:focus-visible{outline:2px solid var(--amber); outline-offset:1px}
  #stapp .stage{display:grid; grid-template-columns:minmax(0,1fr) 268px; gap:12px; align-items:start}
  @media (max-width:860px){ #stapp .stage{grid-template-columns:1fr} }
  #stapp .board{background:var(--panel2); border:1px solid var(--edge); border-radius:10px;
    padding:10px; position:relative}
  #stapp canvas{display:block; width:100%; height:auto; border-radius:6px}
  #stapp .verdict{position:absolute; top:18px; right:18px; font-family:var(--mono);
    font-size:11px; letter-spacing:.12em; padding:4px 10px; border-radius:20px; font-weight:700}
  #stapp .verdict.ok{background:rgba(87,217,138,.14); color:var(--good); border:1px solid rgba(87,217,138,.4)}
  #stapp .verdict.no{background:rgba(255,90,114,.14); color:var(--red); border:1px solid rgba(255,90,114,.4)}
  #stapp .rail{display:flex; flex-direction:column; gap:12px}
  #stapp .card{background:var(--panel); border:1px solid var(--edge); border-radius:10px; padding:12px 13px}
  #stapp .card h3{margin:0 0 9px; font-size:10.5px; letter-spacing:.16em; text-transform:uppercase;
    color:var(--ink-faint); font-weight:600}
  #stapp .stat{display:flex; justify-content:space-between; align-items:baseline; padding:3px 0;
    font-family:var(--mono); font-size:12.5px}
  #stapp .stat .k{color:var(--ink-dim); letter-spacing:.02em}
  #stapp .stat .v{font-variant-numeric:tabular-nums; font-weight:600}
  #stapp .dot{display:inline-block; width:8px; height:8px; border-radius:2px; margin-right:7px; vertical-align:1px}
  #stapp .dot.rnd{border-radius:50%}
  #stapp .clock{font-family:var(--mono); font-size:25px; font-weight:700; font-variant-numeric:tabular-nums;
    letter-spacing:.02em; color:var(--ink)}
  #stapp .clock small{font-size:12px; color:var(--ink-dim); font-weight:400; margin-left:6px}
  #stapp .bar{height:7px; border-radius:4px; background:#1b2732; overflow:hidden; margin-top:5px}
  #stapp .bar > i{display:block; height:100%; background:linear-gradient(90deg,#8a5a12,var(--amber)); width:0}
  #stapp .params{font-family:var(--mono); font-size:11.5px; line-height:1.65; color:var(--ink-dim); word-break:break-word}
  #stapp .params b{color:var(--ink)}
  #stapp .transport{display:flex; align-items:center; gap:10px; margin-top:10px; flex-wrap:wrap}
  #stapp button.tp{background:var(--panel); color:var(--ink); border:1px solid var(--edge);
    border-radius:7px; padding:8px 12px; font-family:var(--mono); font-size:12px; cursor:pointer; min-width:40px}
  #stapp button.tp:hover{border-color:var(--amber); color:#fff}
  #stapp button.tp:focus-visible{outline:2px solid var(--amber); outline-offset:1px}
  #stapp button.tp.play{background:var(--amber); color:#0a0e13; border-color:var(--amber); font-weight:700}
  #stapp .speeds{display:flex; gap:4px; margin-left:auto}
  #stapp button.sp{background:transparent; color:var(--ink-dim); border:1px solid var(--edge);
    border-radius:6px; padding:6px 9px; font-family:var(--mono); font-size:11px; cursor:pointer}
  #stapp button.sp.on{background:var(--panel); color:var(--amber); border-color:var(--amber)}
  #stapp .scrub{display:flex; align-items:center; gap:11px; margin-top:11px; font-family:var(--mono); font-size:11px; color:var(--ink-dim)}
  #stapp input[type=range]{flex:1; accent-color:var(--amber); height:4px}
  #stapp .spark{margin-top:12px}
  #stapp .legend{display:flex; flex-wrap:wrap; gap:11px 16px; font-size:11px; color:var(--ink-dim); font-family:var(--mono)}
  #stapp .foot{color:var(--ink-faint); font-size:11px; font-family:var(--mono); letter-spacing:.02em; margin-top:2px}
</style>

<div id="stapp">
  <div class="head">
    <span class="brand">SandTable <b>&#9679;</b> Mission Replay</span>
    <span class="sub">Mission-level ProjectGL testbed &nbsp;&middot;&nbsp; FP6111 VIPR-GS HMT &nbsp;&middot;&nbsp;
      <span class="mono">representative runs recorded from run_mission</span></span>
    <select id="pick" aria-label="Select recorded mission"></select>
  </div>

  <div class="stage">
    <div>
      <div class="board">
        <canvas id="cv" width="1200" height="600" role="img" aria-label="Battlefield replay"></canvas>
        <span id="verdict" class="verdict"></span>
      </div>
      <div class="transport">
        <button class="tp" id="restart" title="Restart">&#8635;</button>
        <button class="tp" id="stepb" title="Step back">&#9664;</button>
        <button class="tp play" id="play" title="Play / pause">&#9654;</button>
        <button class="tp" id="stepf" title="Step forward">&#9654;&#9654;</button>
        <button class="tp" id="loop" title="Loop" style="min-width:auto">loop</button>
        <div class="speeds">
          <button class="sp" data-s="0.5">0.5&times;</button>
          <button class="sp on" data-s="1">1&times;</button>
          <button class="sp" data-s="2">2&times;</button>
          <button class="sp" data-s="4">4&times;</button>
        </div>
      </div>
      <div class="scrub">
        <span id="tnow">T+0000s</span>
        <input type="range" id="seek" min="0" max="100" value="0" step="0.01" aria-label="Timeline">
        <span id="tend">/ 0000s</span>
      </div>
      <div class="spark card" style="padding:10px 12px">
        <canvas id="spk" width="1200" height="150" style="width:100%;height:auto"></canvas>
      </div>
    </div>

    <div class="rail">
      <div class="card">
        <h3>Mission clock</h3>
        <div class="clock"><span id="clk">0</span><small>s &nbsp;/&nbsp; frame <span id="fidx">0</span></small></div>
      </div>
      <div class="card">
        <h3>Force status</h3>
        <div class="stat"><span class="k"><span class="dot rnd" style="background:var(--blue)"></span>Blue ground</span><span class="v" id="s_bg">0</span></div>
        <div class="stat"><span class="k"><span class="dot" style="background:var(--air);border-radius:50% 50% 2px 2px"></span>Blue air (UAS)</span><span class="v" id="s_ba">0</span></div>
        <div class="stat"><span class="k"><span class="dot" style="background:var(--red)"></span>Red force</span><span class="v" id="s_r">0</span></div>
        <div class="stat"><span class="k"><span class="dot rnd" style="background:var(--amber)"></span>Red detected</span><span class="v" id="s_seen">0</span></div>
      </div>
      <div class="card">
        <h3>Detection coverage</h3>
        <div class="stat"><span class="k">live</span><span class="v" id="cov_now">0%</span></div>
        <div class="bar"><i id="cov_bar"></i></div>
        <div class="stat" style="margin-top:8px"><span class="k">mission avg</span><span class="v" id="cov_avg">0%</span></div>
      </div>
      <div class="card">
        <h3>Typical outcome <span id="aggn" style="text-transform:none;letter-spacing:0"></span></h3>
        <div class="stat"><span class="k">success rate</span><span class="v" id="a_succ">—</span></div>
        <div class="stat"><span class="k">blue losses (avg)</span><span class="v" id="a_bl">—</span></div>
        <div class="stat"><span class="k">red losses (avg)</span><span class="v" id="a_rl">—</span></div>
        <div class="stat"><span class="k">coverage (avg)</span><span class="v" id="a_cov">—</span></div>
      </div>
      <div class="card">
        <h3>Run parameters</h3>
        <div class="params" id="params"></div>
      </div>
      <div class="card">
        <h3>Legend</h3>
        <div class="legend">
          <span><span class="dot rnd" style="background:var(--blue)"></span>UGV</span>
          <span><span class="dot" style="background:var(--air);border-radius:50% 50% 2px 2px"></span>UAS</span>
          <span><span class="dot" style="background:var(--red)"></span>Threat</span>
          <span><span class="dot rnd" style="border:1.5px solid var(--amber);background:transparent"></span>detected</span>
          <span><span class="dot" style="background:var(--ink-faint)"></span>killed</span>
        </div>
      </div>
    </div>
  </div>
  <div class="foot" id="foot"></div>
</div>

<script>
(function(){
  const TRACES = /*__TRACES__*/;
  const BLUE=0, RED=1, GROUND=0, AIR=1;
  const C = {blue:"#4fb0ff", air:"#37e6cf", red:"#ff5a72", amber:"#ffb03a",
             dead:"#54626f", good:"#57d98a", ink:"#cdd8e3", grid:"#1b2732"};

  const cv=document.getElementById("cv"), ctx=cv.getContext("2d");
  const spk=document.getElementById("spk"), sctx=spk.getContext("2d");
  const pick=document.getElementById("pick");

  // group the traces into <optgroup>s
  const groups={};
  TRACES.forEach((t,i)=>{ (groups[t.group]=groups[t.group]||[]).push(i); });
  Object.keys(groups).forEach(g=>{
    const og=document.createElement("optgroup"); og.label=g;
    groups[g].forEach(i=>{ const o=document.createElement("option"); o.value=i; o.textContent=TRACES[i].label; og.appendChild(o); });
    pick.appendChild(og);
  });

  let T=null;           // current trace
  let series=[];        // per-frame aggregates
  let terrainCanvas=null;
  let head=0;           // playhead in frame-index units (float)
  let playing=false, speed=1, looping=false;
  const FPS=9;          // frame-indices advanced per second at 1x
  let lastTs=null;

  function prep(idx){
    T=TRACES[idx];
    head=0; playing=false; updatePlayBtn();
    // per-frame aggregates for the rail + sparklines
    series=T.frames.map(f=>{
      let bg=0,ba=0,ra=0,rs=0;
      T.entities.forEach((e,i)=>{
        if(e.side===BLUE){ if(f.alive[i]){ e.domain===GROUND?bg++:ba++; } }
        else if(f.alive[i]){ ra++; if(f.seen[i]) rs++; }
      });
      return {t:f.t, bg, ba, ra, rs, cov: ra>0? rs/ra : 0};
    });
    buildTerrain();
    // fixed force denominators (frame 0)
    const f0=T.frames[0]; let BG=0,BA=0,R=0;
    T.entities.forEach((e,i)=>{ if(e.side===BLUE){ e.domain===GROUND?BG++:BA++; } else R++; });
    T._den={BG,BA,R};
    // params + verdict + labels
    const p=T.params, keys=Object.keys(p);
    document.getElementById("params").innerHTML =
      keys.map(k=>`${k} = <b>${typeof p[k]==="number"? (Number.isInteger(p[k])?p[k]:p[k].toFixed(2)) : p[k]}</b>`).join("<br>");
    const v=document.getElementById("verdict"), ok=T.outcome.success>=1;
    v.className="verdict "+(ok?"ok":"no"); v.textContent=ok?"MISSION SUCCESS":"MISSION FAILURE";
    const cov=(T.outcome.detection_coverage*100).toFixed(0);
    document.getElementById("cov_avg").textContent=cov+"%";
    document.getElementById("tend").textContent="/ "+String(Math.round(T.frames[T.frames.length-1].t)).padStart(4,"0")+"s";
    // multi-seed aggregate (honest context for this single replay)
    const a=T.aggregate;
    document.getElementById("aggn").textContent = a? `(n=${a.n})` : "";
    if(a){
      document.getElementById("a_succ").textContent=(a.success_rate*100).toFixed(0)+"%";
      document.getElementById("a_bl").textContent=a.blue_losses.toFixed(1);
      document.getElementById("a_rl").textContent=a.red_losses.toFixed(1);
      document.getElementById("a_cov").textContent=(a.detection_coverage*100).toFixed(0)+"%";
    }
    document.getElementById("foot").textContent =
      `${T.name}  ·  representative run (seed ${T.seed}) of ${a?a.n:"?"}  ·  ${T.frames.length} frames  ·  `+
      `this run: blue losses ${T.outcome.blue_losses}, red losses ${T.outcome.red_losses}, mission time ${Math.round(T.outcome.mission_time)}s  ·  `+
      `world ${T.size[0]}×${T.size[1]} m`;
    resize();
  }

  // ----- geometry -----
  let DW=1200, DH=600, PAD=26, sc=1;
  function resize(){
    const cssW=Math.max(320, cv.parentElement.clientWidth-20);
    const agg=T? T.size[1]/T.size[0] : 0.5;
    const cssH=Math.round(cssW*agg);
    const dpr=Math.min(window.devicePixelRatio||1, 2);
    cv.width=cssW*dpr; cv.height=cssH*dpr; cv.style.height=cssH+"px";
    ctx.setTransform(dpr,0,0,dpr,0,0);
    DW=cssW; DH=cssH; PAD=Math.round(cssW*0.02);
    sc=(DW-2*PAD)/T.size[0];
    // sparkline canvas
    const sw=cssW, sh=150;
    spk.width=sw*dpr; spk.height=sh*dpr; spk.style.height=sh+"px";
    sctx.setTransform(dpr,0,0,dpr,0,0); spk._w=sw; spk._h=sh;
    draw();
  }
  const X=x=> PAD + x*sc;
  const Y=y=> PAD + y*sc;

  // ----- terrain prerender (static per trace) -----
  function buildTerrain(){
    const cov=T.terrain.cover, ny=cov.length, nx=cov[0].length;
    const oc=document.createElement("canvas"); oc.width=nx; oc.height=ny;
    const octx=oc.getContext("2d"); const img=octx.createImageData(nx,ny);
    const con=T.terrain.conceal;
    for(let j=0;j<ny;j++)for(let i=0;i<nx;i++){
      const c=cov[j][i], k=con? con[j][i]:0, o=(j*nx+i)*4;
      // open ground = cool slate; cover = olive green; concealment = slight blue lift
      const r=18+ c*36 + k*4, g=26 + c*74 + k*10, b=34 + c*20 + k*30;
      img.data[o]=r; img.data[o+1]=g; img.data[o+2]=b; img.data[o+3]=255;
    }
    octx.putImageData(img,0,0);
    terrainCanvas={cv:oc,nx,ny};
  }

  // ----- interpolation helpers -----
  function frameAt(h){ return Math.max(0, Math.min(T.frames.length-1, Math.floor(h))); }
  function lerp(a,b,t){ return a+(b-a)*t; }
  function pos(i,h){
    const fi=frameAt(h), nx=Math.min(fi+1,T.frames.length-1), fr=h-fi;
    const A=T.frames[fi], B=T.frames[nx];
    // freeze dead units at their death frame position
    const t = (A.alive[i] && B.alive[i]) ? fr : 0;
    return [lerp(A.x[i],B.x[i],t), lerp(A.y[i],B.y[i],t)];
  }

  // ----- main draw -----
  function draw(){
    if(!T) return;
    const fi=frameAt(head), f=T.frames[fi];
    ctx.clearRect(0,0,DW,DH);
    // terrain
    if(terrainCanvas){ ctx.imageSmoothingEnabled=true;
      ctx.drawImage(terrainCanvas.cv, PAD, PAD, T.size[0]*sc, T.size[1]*sc); }
    // km grid
    ctx.strokeStyle=C.grid; ctx.lineWidth=1; ctx.font="10px "+"ui-monospace,monospace"; ctx.fillStyle="#33424f";
    for(let gx=0; gx<=T.size[0]; gx+=1000){ ctx.beginPath(); ctx.moveTo(X(gx),PAD); ctx.lineTo(X(gx),PAD+T.size[1]*sc); ctx.stroke(); }
    for(let gy=0; gy<=T.size[1]; gy+=1000){ ctx.beginPath(); ctx.moveTo(PAD,Y(gy)); ctx.lineTo(PAD+T.size[0]*sc,Y(gy)); ctx.stroke(); }
    // objective
    const gx=T.objective.goal[0], gy=T.objective.goal[1], gr=T.objective.radius*sc;
    ctx.strokeStyle=C.amber; ctx.lineWidth=1.5; ctx.setLineDash([4,4]);
    ctx.beginPath(); ctx.arc(X(gx),Y(gy),Math.max(gr,10),0,7); ctx.stroke(); ctx.setLineDash([]);
    ctx.beginPath(); ctx.moveTo(X(gx)-8,Y(gy)); ctx.lineTo(X(gx)+8,Y(gy)); ctx.moveTo(X(gx),Y(gy)-8); ctx.lineTo(X(gx),Y(gy)+8); ctx.stroke();
    ctx.fillStyle=C.amber; ctx.font="10px ui-monospace,monospace"; ctx.fillText("OBJ", X(gx)+11, Y(gy)-9);

    // trails (recent path per living entity)
    const TR=6;
    T.entities.forEach((e,i)=>{
      if(!f.alive[i]) return;
      ctx.beginPath();
      for(let k=Math.max(0,fi-TR);k<=fi;k++){ const p=T.frames[k]; const xx=X(p.x[i]), yy=Y(p.y[i]);
        k===Math.max(0,fi-TR)?ctx.moveTo(xx,yy):ctx.lineTo(xx,yy); }
      ctx.strokeStyle = e.side===BLUE ? (e.domain===AIR?"rgba(55,230,207,.30)":"rgba(79,176,255,.28)") : "rgba(255,90,114,.22)";
      ctx.lineWidth=1.5; ctx.stroke();
    });

    // UAS sensor rings first (under glyphs)
    T.entities.forEach((e,i)=>{
      if(e.side===BLUE && e.domain===AIR && f.alive[i] && e.sensor_range>0){
        const [x,y]=pos(i,head);
        ctx.beginPath(); ctx.arc(X(x),Y(y), e.sensor_range*sc, 0, 7);
        ctx.strokeStyle="rgba(55,230,207,.16)"; ctx.lineWidth=1; ctx.stroke();
      }
    });

    // death flashes (unit alive last frame, dead now)
    if(fi>0){ const pf=T.frames[fi-1];
      T.entities.forEach((e,i)=>{
        if(pf.alive[i] && !f.alive[i]){ const xx=X(f.x[i]), yy=Y(f.y[i]);
          ctx.beginPath(); ctx.arc(xx,yy,9,0,7); ctx.strokeStyle="rgba(255,220,120,.8)"; ctx.lineWidth=2; ctx.stroke(); }
      });
    }

    // entities
    T.entities.forEach((e,i)=>{
      const alive=f.alive[i], [x,y]=pos(i,head), sx=X(x), sy=Y(y);
      if(e.side===RED){
        const s=5;
        if(alive){
          ctx.fillStyle=C.red; ctx.fillRect(sx-s,sy-s,2*s,2*s);
          if(f.seen[i]){ ctx.strokeStyle=C.amber; ctx.lineWidth=2; ctx.beginPath(); ctx.arc(sx,sy,s+4,0,7); ctx.stroke(); }
        } else { ctx.strokeStyle=C.dead; ctx.lineWidth=1.4;
          ctx.beginPath(); ctx.moveTo(sx-4,sy-4); ctx.lineTo(sx+4,sy+4); ctx.moveTo(sx+4,sy-4); ctx.lineTo(sx-4,sy+4); ctx.stroke(); }
      } else if(e.domain===AIR){
        if(alive){ ctx.fillStyle=C.air; ctx.beginPath();
          ctx.moveTo(sx,sy-6); ctx.lineTo(sx+5.5,sy+4); ctx.lineTo(sx-5.5,sy+4); ctx.closePath(); ctx.fill();
        } else { ctx.strokeStyle=C.dead; ctx.lineWidth=1.4; ctx.beginPath();
          ctx.moveTo(sx,sy-6); ctx.lineTo(sx+5.5,sy+4); ctx.lineTo(sx-5.5,sy+4); ctx.closePath(); ctx.stroke(); }
      } else { // blue ground; brightness encodes control quality
        const q = f.cq? f.cq[i] : 1;
        if(alive){
          const g=Math.round(120+135*q);
          ctx.fillStyle=`rgb(${Math.round(60+20*q)},${Math.round(140+40*q)},${g+40>255?255:g+40})`;
          ctx.beginPath(); ctx.arc(sx,sy,5.5,0,7); ctx.fill();
          if(q<0.999){ ctx.strokeStyle="rgba(255,176,58,.5)"; ctx.lineWidth=1; ctx.beginPath(); ctx.arc(sx,sy,5.5,0,7); ctx.stroke(); }
        } else { ctx.strokeStyle=C.dead; ctx.lineWidth=1.4;
          ctx.beginPath(); ctx.moveTo(sx-4,sy-4); ctx.lineTo(sx+4,sy+4); ctx.moveTo(sx+4,sy-4); ctx.lineTo(sx-4,sy+4); ctx.stroke(); }
      }
    });

    updateRail(fi);
    drawSpark(fi);
  }

  function updateRail(fi){
    const s=series[fi], d=T._den;
    document.getElementById("clk").textContent=Math.round(T.frames[fi].t);
    document.getElementById("fidx").textContent=fi;
    document.getElementById("s_bg").textContent=`${s.bg} / ${d.BG}`;
    document.getElementById("s_ba").textContent= d.BA? `${s.ba} / ${d.BA}` : "—";
    document.getElementById("s_r").textContent=`${s.ra} / ${d.R}`;
    document.getElementById("s_seen").textContent=s.rs;
    document.getElementById("cov_now").textContent=Math.round(s.cov*100)+"%";
    document.getElementById("cov_bar").style.width=(s.cov*100)+"%";
    document.getElementById("tnow").textContent="T+"+String(Math.round(T.frames[fi].t)).padStart(4,"0")+"s";
    document.getElementById("seek").value=(head/(T.frames.length-1)*100).toFixed(2);
  }

  // ----- sparklines: coverage area + force counts, shared playhead -----
  function drawSpark(fi){
    const W=spk._w, H=spk._h, n=series.length;
    sctx.clearRect(0,0,W,H);
    const padL=34, padR=8, padT=12, midY=Math.round(H*0.52), botY=H-16;
    const xAt=k=> padL + (W-padL-padR)*(k/(n-1||1));
    // coverage area (top band, 0..1)
    sctx.fillStyle="rgba(255,176,58,.16)"; sctx.strokeStyle=C.amber; sctx.lineWidth=1.5;
    sctx.beginPath(); sctx.moveTo(padL,midY);
    series.forEach((s,k)=> sctx.lineTo(xAt(k), midY-(midY-padT)*s.cov));
    sctx.lineTo(xAt(n-1),midY); sctx.closePath(); sctx.fill();
    sctx.beginPath(); series.forEach((s,k)=>{ const y=midY-(midY-padT)*s.cov; k?sctx.lineTo(xAt(k),y):sctx.moveTo(xAt(k),y); }); sctx.stroke();
    sctx.fillStyle="#8a6a2a"; sctx.font="9px ui-monospace,monospace"; sctx.fillText("coverage",padL,padT-2);
    // force counts (bottom band)
    const maxC=Math.max(T._den.BG+T._den.BA, T._den.R, 1);
    const line=(key,color)=>{ sctx.strokeStyle=color; sctx.lineWidth=1.5; sctx.beginPath();
      series.forEach((s,k)=>{ const val = key==="b"? (s.bg+s.ba): s.ra; const y=botY-(botY-midY-10)*(val/maxC);
        k?sctx.lineTo(xAt(k),y):sctx.moveTo(xAt(k),y); }); sctx.stroke(); };
    line("b",C.blue); line("r",C.red);
    sctx.fillStyle="#3f5163"; sctx.fillText("forces alive",padL,midY+11);
    // axis baseline
    sctx.strokeStyle=C.grid; sctx.beginPath(); sctx.moveTo(padL,botY); sctx.lineTo(W-padR,botY); sctx.stroke();
    // playhead
    const px=xAt(fi); sctx.strokeStyle="rgba(255,255,255,.5)"; sctx.lineWidth=1;
    sctx.beginPath(); sctx.moveTo(px,padT-4); sctx.lineTo(px,botY); sctx.stroke();
  }

  // ----- transport -----
  function updatePlayBtn(){ document.getElementById("play").innerHTML = playing? "&#10073;&#10073;" : "&#9654;"; }
  function tick(ts){
    if(playing){
      if(lastTs==null) lastTs=ts;
      const dt=(ts-lastTs)/1000; lastTs=ts;
      head += dt*FPS*speed;
      const last=T.frames.length-1;
      if(head>=last){ if(looping){ head=0; } else { head=last; playing=false; updatePlayBtn(); } }
      draw();
    } else lastTs=null;
    requestAnimationFrame(tick);
  }
  document.getElementById("play").onclick=()=>{ if(head>=T.frames.length-1) head=0; playing=!playing; lastTs=null; updatePlayBtn(); };
  document.getElementById("restart").onclick=()=>{ head=0; draw(); };
  document.getElementById("stepf").onclick=()=>{ playing=false; updatePlayBtn(); head=Math.min(T.frames.length-1,Math.floor(head)+1); draw(); };
  document.getElementById("stepb").onclick=()=>{ playing=false; updatePlayBtn(); head=Math.max(0,Math.ceil(head)-1); draw(); };
  document.getElementById("loop").onclick=(e)=>{ looping=!looping; e.target.style.color=looping?C.amber:""; e.target.style.borderColor=looping?C.amber:""; };
  document.querySelectorAll(".sp").forEach(b=> b.onclick=()=>{ speed=parseFloat(b.dataset.s);
    document.querySelectorAll(".sp").forEach(x=>x.classList.remove("on")); b.classList.add("on"); });
  document.getElementById("seek").oninput=(e)=>{ playing=false; updatePlayBtn(); head=(e.target.value/100)*(T.frames.length-1); draw(); };
  pick.onchange=()=>prep(parseInt(pick.value,10));
  window.addEventListener("resize", ()=>{ if(T) resize(); });

  prep(0);
  requestAnimationFrame(tick);
})();
</script>
"""

if __name__ == "__main__":
    main()
