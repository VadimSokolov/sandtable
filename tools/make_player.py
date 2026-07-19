"""Build a simple, self-contained mission result player.

A deliberately minimal alternative to tools/make_viz.py: a plain map, unit markers, play/pause, and a
scrubber. Same trustworthy data source (the representative traces from make_viz, recorded step-for-
step from run_mission) but a small, readable viewer built from scratch.

Run:  PYTHONPATH=src python tools/make_player.py
"""
from __future__ import annotations

import json
from pathlib import Path

from make_viz import build_traces  # reuse the validated representative-trace recorder


def main() -> None:
    print("Recording representative traces for the simple player:")
    traces = build_traces()
    payload = json.dumps(traces, separators=(",", ":"))
    inner = TEMPLATE.replace("/*__TRACES__*/", payload)

    out_dir = Path("report/viz")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "_player_body.html").write_text(inner)
    standalone = (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
        "<title>SandTable Result Player</title>\n</head>\n<body>\n" + inner + "\n</body>\n</html>\n"
    )
    (out_dir / "player.html").write_text(standalone)
    print(f"\nWrote {out_dir/'player.html'}  ({len(standalone)/1024:.0f} KB)")
    print(f"Wrote {out_dir/'_player_body.html'}  (Artifact body fragment)")


TEMPLATE = r"""<style>
  #player{--ink:#1c2530;--muted:#7a8798;--line:#dde3ea;--paper:#ffffff;--panel:#f4f6f9;
    --blue:#2f6fed;--red:#e5484d;--amber:#e8912a;--good:#1f9d57;
    font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:var(--ink);
    background:var(--panel);min-height:100vh;box-sizing:border-box;padding:22px;
    display:flex;flex-direction:column;align-items:center;gap:14px}
  #player *{box-sizing:border-box}
  #player .wrap{width:100%;max-width:900px;display:flex;flex-direction:column;gap:12px}
  #player .top{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
  #player h1{font-size:16px;margin:0;font-weight:650;letter-spacing:.01em}
  #player h1 span{color:var(--muted);font-weight:400;font-size:13px}
  #player select{margin-left:auto;font-size:13px;padding:7px 10px;border:1px solid var(--line);
    border-radius:8px;background:var(--paper);color:var(--ink);min-width:280px}
  #player .map{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:8px}
  #player canvas{display:block;width:100%;height:auto;border-radius:8px}
  #player .ctrls{display:flex;align-items:center;gap:12px}
  #player button{border:1px solid var(--line);background:var(--paper);color:var(--ink);
    border-radius:8px;padding:8px 14px;font-size:13px;cursor:pointer;font-variant-numeric:tabular-nums}
  #player button:hover{border-color:var(--muted)}
  #player button:focus-visible{outline:2px solid var(--blue);outline-offset:1px}
  #player button.go{background:var(--blue);border-color:var(--blue);color:#fff;font-weight:600;min-width:78px}
  #player input[type=range]{flex:1;accent-color:var(--blue)}
  #player .t{font-family:ui-monospace,Menlo,monospace;font-size:13px;color:var(--muted);
    font-variant-numeric:tabular-nums;min-width:64px}
  #player .row{display:flex;align-items:center;gap:16px;flex-wrap:wrap;font-size:13px;color:var(--muted)}
  #player .row b{color:var(--ink);font-variant-numeric:tabular-nums}
  #player .key{display:inline-flex;align-items:center;gap:6px}
  #player .sw{width:11px;height:11px;border-radius:50%;display:inline-block}
  #player .sw.sq{border-radius:2px}
  #player .verdict{font-weight:650}
  #player .verdict.ok{color:var(--good)}
  #player .verdict.no{color:var(--red)}
</style>

<div id="player">
  <div class="wrap">
    <div class="top">
      <h1>Mission Result Player <span>&middot; mission-level ProjectGL</span></h1>
      <select id="run" aria-label="Choose a run"></select>
    </div>

    <div class="map"><canvas id="c" width="900" height="450"></canvas></div>

    <div class="ctrls">
      <button class="go" id="play">Play</button>
      <input type="range" id="seek" min="0" max="100" value="0" step="1" aria-label="Timeline">
      <span class="t" id="time">0s</span>
      <button id="spd" title="Playback speed">1&times;</button>
    </div>

    <div class="row">
      <span class="key"><span class="sw" style="background:#2f6fed"></span>UGV</span>
      <span class="key"><span class="sw" style="background:#2f6fed;clip-path:polygon(50% 0,100% 100%,0 100%);border-radius:0"></span>UAS</span>
      <span class="key"><span class="sw sq" style="background:#e5484d"></span>threat</span>
      <span class="key"><span class="sw" style="border:2px solid #e8912a;background:transparent"></span>detected</span>
      <span style="margin-left:auto">blue <b id="nb">0</b> &nbsp; red <b id="nr">0</b> &nbsp; seen <b id="ns">0</b></span>
    </div>
    <div class="row" id="meta"></div>
  </div>
</div>

<script>
(function(){
  const TRACES = /*__TRACES__*/;
  const c=document.getElementById("c"), ctx=c.getContext("2d"), run=document.getElementById("run");
  const BLUE=0, AIR=1;

  TRACES.forEach((t,i)=>{ const o=document.createElement("option"); o.value=i;
    o.textContent=t.group.replace(/\s+/g," ").trim()+" — "+t.label; run.appendChild(o); });

  let T, frame=0, playing=false, speed=1, acc=0, last=0;

  function load(i){
    T=TRACES[i]; frame=0; playing=false; document.getElementById("play").textContent="Play";
    document.getElementById("seek").max=T.frames.length-1;
    const a=T.aggregate, ok=T.outcome.success>=1;
    document.getElementById("meta").innerHTML =
      `<span class="verdict ${ok?"ok":"no"}">${ok?"SUCCESS":"FAILURE"}</span>`+
      `<span>example run &middot; seed ${T.seed}</span>`+
      (a?`<span>typical: <b>${(a.success_rate*100).toFixed(0)}%</b> success over ${a.n} runs</span>`:``)+
      `<span>${T.params.control_mode?("control "+T.params.control_mode+" &middot; "):""}`+
      `${T.params.comms_level!=null?("comms C"+T.params.comms_level):""}</span>`;
    fit(); render();
  }

  function fit(){
    const w=c.parentElement.clientWidth-16, h=w*(T.size[1]/T.size[0]);
    const dpr=Math.min(window.devicePixelRatio||1,2);
    c.width=w*dpr; c.height=h*dpr; c.style.height=h+"px";
    ctx.setTransform(dpr,0,0,dpr,0,0); c._w=w; c._h=h;
  }

  function render(){
    const W=c._w, H=c._h, pad=14, sx=(W-2*pad)/T.size[0], sy=(H-2*pad)/T.size[1];
    const X=x=>pad+x*sx, Y=y=>pad+y*sy, f=T.frames[frame];
    ctx.clearRect(0,0,W,H);
    // faint 1 km grid
    ctx.strokeStyle="#eef1f5"; ctx.lineWidth=1;
    for(let g=0; g<=T.size[0]; g+=1000){ ctx.beginPath(); ctx.moveTo(X(g),Y(0)); ctx.lineTo(X(g),Y(T.size[1])); ctx.stroke(); }
    for(let g=0; g<=T.size[1]; g+=1000){ ctx.beginPath(); ctx.moveTo(X(0),Y(g)); ctx.lineTo(X(T.size[0]),Y(g)); ctx.stroke(); }
    // objective
    const gx=T.objective.goal[0], gy=T.objective.goal[1];
    ctx.strokeStyle="#e8912a"; ctx.lineWidth=1.5; ctx.setLineDash([4,3]);
    ctx.beginPath(); ctx.arc(X(gx),Y(gy),Math.max(T.objective.radius*sx,9),0,7); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle="#e8912a"; ctx.font="10px ui-monospace,monospace"; ctx.fillText("OBJ",X(gx)+9,Y(gy)-8);
    // entities
    let nb=0,nr=0,ns=0;
    T.entities.forEach((e,i)=>{
      const x=X(f.x[i]), y=Y(f.y[i]), alive=f.alive[i];
      if(e.side!==BLUE){
        if(alive){ nr++; ctx.fillStyle="#e5484d"; ctx.fillRect(x-4,y-4,8,8);
          if(f.seen[i]){ ns++; ctx.strokeStyle="#e8912a"; ctx.lineWidth=2; ctx.beginPath(); ctx.arc(x,y,8,0,7); ctx.stroke(); } }
        else deadX(x,y);
        return;
      }
      if(alive) nb++;
      if(!alive){ deadX(x,y); return; }
      ctx.fillStyle="#2f6fed";
      if(e.domain===AIR){ ctx.beginPath(); ctx.moveTo(x,y-6); ctx.lineTo(x+5,y+4); ctx.lineTo(x-5,y+4); ctx.closePath(); ctx.fill(); }
      else { ctx.beginPath(); ctx.arc(x,y,5,0,7); ctx.fill(); }
    });
    function deadX(x,y){ ctx.strokeStyle="#b7c0cc"; ctx.lineWidth=1.3;
      ctx.beginPath(); ctx.moveTo(x-3.5,y-3.5); ctx.lineTo(x+3.5,y+3.5); ctx.moveTo(x+3.5,y-3.5); ctx.lineTo(x-3.5,y+3.5); ctx.stroke(); }
    document.getElementById("nb").textContent=nb;
    document.getElementById("nr").textContent=nr;
    document.getElementById("ns").textContent=ns;
    document.getElementById("time").textContent=Math.round(f.t)+"s";
    document.getElementById("seek").value=frame;
  }

  function loop(ts){
    if(playing){
      if(!last) last=ts; acc+=(ts-last)/1000; last=ts;
      const step=1/(6*speed);            // ~6 frames/sec at 1x
      while(acc>=step){ acc-=step; frame++;
        if(frame>=T.frames.length-1){ frame=T.frames.length-1; playing=false;
          document.getElementById("play").textContent="Replay"; break; } }
      render();
    } else last=0;
    requestAnimationFrame(loop);
  }

  document.getElementById("play").onclick=()=>{
    if(frame>=T.frames.length-1) frame=0;
    playing=!playing; last=0;
    document.getElementById("play").textContent=playing?"Pause":"Play";
  };
  document.getElementById("seek").oninput=e=>{ playing=false;
    document.getElementById("play").textContent="Play"; frame=+e.target.value; render(); };
  document.getElementById("spd").onclick=e=>{ speed=speed>=4?1:speed*2; e.target.innerHTML=speed+"&times;"; };
  run.onchange=()=>load(+run.value);
  window.addEventListener("resize",()=>{ if(T){ fit(); render(); } });

  load(0);
  requestAnimationFrame(loop);
})();
</script>
"""

if __name__ == "__main__":
    main()
