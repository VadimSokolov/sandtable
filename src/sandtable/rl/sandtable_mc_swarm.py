# sandtable_mc_viz_runner.py
"""
Run SANDTABLE Monte Carlo and visualize results in the mission viewer.
"""

from sandtable.scenario import load_scenario
from sandtable.sim import run_mission, evaluate
from sandtable.replay import record_trace
import numpy as np
import json
import webbrowser
import os
from datetime import datetime
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    filename='mc_swarm.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ============================================================
# 1. Run MC and Find Best Parameters
# ============================================================

def run_mc_optimization(
    scenario_path: str,
    n_agents: int = 5,
    n_steps: int = 15,
    n_reps: int = 10,
    seed: int = 42
) -> dict:
    """Run Monte Carlo to find best parameters."""
    
    print("🐝 Running Monte Carlo Optimization...")
    print("=" * 60)
    
    # Parameter space
    param_ranges = {
        "route_bias": (0.0, 1.0),
        "comms_level": (0, 5),
        "n_blue": (2, 8),
        "tempo": (0.5, 1.0)
    }
    
    # Storage
    all_results = []
    best_reward = -float('inf')
    best_params = None
    best_result: dict | None = None
    
    scn = load_scenario(scenario_path)
    
    for agent in range(n_agents):
        print(f"\n  Agent {agent+1}/{n_agents}")
        
        for step in range(n_steps):
            # Sample random parameters
            params = {
                "route_bias": np.random.uniform(*param_ranges["route_bias"]),
                "comms_level": np.random.randint(*param_ranges["comms_level"]),
                "n_blue": np.random.randint(*param_ranges["n_blue"]),
                "tempo": np.random.uniform(*param_ranges["tempo"])
            }
            
            # Evaluate
            result = evaluate(
                scn, 
                n_reps=n_reps, 
                seed=seed + agent * n_steps + step,
                params=params
            )
            
            # Reward function
            reward = (
                result["success_rate"] * 10.0
                - result["blue_loss_frac"] * 5.0
                + (1.0 - result["time_to_objective"] / 1800.0) * 2.0
            )
            
            all_results.append({
                "params": params.copy(),
                "result": result,
                "reward": reward
            })
            
            if reward > best_reward:
                best_reward = reward
                best_params = params.copy()
                best_result = result
            
            log_msg = (f"Agent {agent+1}/{n_agents} - Step {step+1}: "
                       f"reward={reward:.2f} | success={result['success_rate']:.1%} | "
                       f"losses={result['blue_loss_frac']:.1%} | params={params}")
            logging.info(log_msg)
            
            print(f"    Step {step+1:2d}: reward={reward:6.2f} | "
                  f"success={result['success_rate']:.1%} | "
                  f"losses={result['blue_loss_frac']:.1%}")
    
    logging.info(f"MC Optimization complete. Best reward: {best_reward:.2f}, Best params: {best_params}")
    
    print(f"\n✅ Best reward: {best_reward:.2f}")
    print(f"   Best params: {best_params}")
    print(f"   Success rate: {best_result['success_rate']:.1%}")
    
    return {
        "best_params": best_params,
        "best_result": best_result,
        "all_results": all_results,
        "n_agents": n_agents,
        "n_steps": n_steps,
        "n_reps": n_reps
    }


# ============================================================
# 2. Generate Trace for Viewer
# ============================================================

def generate_viewer_trace(
    scenario_path: str,
    params: dict,
    seed: int = 42,
    stride: int = 5
) -> dict:
    """Generate a trace for the mission viewer."""
    
    print("\n📊 Generating viewer trace...")
    
    scn = load_scenario(scenario_path)
    trace = record_trace(scn, seed=seed, params=params, stride=stride)
    
    # Add metadata for viewer
    trace["seed"] = seed
    trace["group"] = "MC Optimized"
    trace["label"] = f"MC Best: route={params.get('route_bias',0):.2f}, comms={params.get('comms_level',0)}, n={params.get('n_blue',0)}"
    
    # Add aggregate (for the viewer's "Typical outcome" panel)
    # Run a small MC to get aggregate stats
    result = evaluate(scn, n_reps=10, seed=seed + 999, params=params)
    trace["aggregate"] = {
        "n": 10,
        "success_rate": result["success_rate"],
        "blue_losses": result["blue_losses"],
        "red_losses": result["red_losses"],
        "detection_coverage": result.get("detection_coverage", 0.0)
    }
    
    print(f"  ✓ Trace generated: {len(trace['frames'])} frames")
    print(f"  ✓ Outcome: {'SUCCESS' if trace['outcome']['success'] else 'FAILURE'}")
    
    return trace


# ============================================================
# 3. Inject Trace into Viewer HTML
# ============================================================

def find_viewer_template() -> str:
    """Find the viewer template in various possible locations."""
    
    base_dir = Path(__file__).parent
    
    # Known locations from file structure, relative to this script
    possible_paths = [
        base_dir / "../../report/viz/mission_viewer.html",
        Path.cwd() / "report/viz/mission_viewer.html",
        Path.cwd() / "../report/viz/mission_viewer.html",
        Path.cwd() / "../../report/viz/mission_viewer.html",
    ]
    
    for path in possible_paths:
        resolved = path.resolve()
        if resolved.exists():
            return str(resolved)
    
    # If not found, look for any .html file in the whole project
    project_root = base_dir.parent.parent
    for html_file in project_root.rglob("mission_viewer.html"):
        return str(html_file)
    
    raise FileNotFoundError(
        "mission_viewer.html not found. Please provide the full path:\n"
        "inject_trace_into_viewer(trace, viewer_template='/path/to/mission_viewer.html')"
    )


def inject_trace_into_viewer(
    trace: dict,
    viewer_template: str |None = None,
    output_file: str|None = None
) -> str:
    """Inject trace into the viewer HTML."""
    
    if viewer_template is None:
        viewer_template = find_viewer_template()
    
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"mission_viewer_mc_{timestamp}.html"
    
    print(f"  📄 Using template: {viewer_template}")
    
    # Read template
    with open(viewer_template, "r") as f:
        html = f.read()
    
    # Find the TRACES array and replace it
    import re
    
    # Convert trace to JSON
    traces_json = json.dumps([trace], indent=2)
    
    # Replace the TRACES array in the HTML
    pattern = r'const TRACES = \[.*?\];'
    replacement = f'const TRACES = {traces_json};'
    
    html = re.sub(pattern, replacement, html, flags=re.DOTALL)
    
    # Also update the default view to select the first trace
    html = html.replace('DEFAULT_VIEW = 7;', 'DEFAULT_VIEW = 0;')
    
    # Write output
    with open(output_file, "w") as f:
        f.write(html)
    
    # Get absolute path
    abs_path = Path(output_file).absolute()
    print(f"  ✅ Viewer saved to: {abs_path}")
    
    return str(abs_path)


# ============================================================
# 4. Main Workflow
# ============================================================

def run_mc_to_viewer(
    scenario_path: str = "scenarios/sc_span_control.json",
    n_agents: int = 5,
    n_steps: int = 10,
    n_reps: int = 8,
    seed: int = 42,
    open_browser: bool = True,
    viewer_template: str|None = None
):
    """Complete workflow: MC optimization → trace → viewer."""
    
    print("🚀 SANDTABLE Monte Carlo to Viewer")
    print("=" * 70)
    print(f"  Scenario: {scenario_path}")
    print(f"  Agents: {n_agents}")
    print(f"  Steps per agent: {n_steps}")
    print(f"  Replications: {n_reps}")
    print("=" * 70)
    
    # Step 1: Run MC optimization
    mc_results = run_mc_optimization(
        scenario_path=scenario_path,
        n_agents=n_agents,
        n_steps=n_steps,
        n_reps=n_reps,
        seed=seed
    )
    
    # Step 2: Generate trace for best params
    trace = generate_viewer_trace(
        scenario_path=scenario_path,
        params=mc_results["best_params"],
        seed=seed + 1000
    )
    
    # Step 3: Inject into viewer
    viewer_file = inject_trace_into_viewer(trace, viewer_template=viewer_template)
    
    # Step 4: Open in browser
    if open_browser:
        webbrowser.open(f"file://{viewer_file}")
        print(f"\n🌐 Viewer opened in browser")
    
    print("\n✅ Done!")
    
    return {
        "mc_results": mc_results,
        "trace": trace,
        "viewer_file": viewer_file
    }


# ============================================================
# 5. Batch Run: Multiple Scenarios
# ============================================================

def run_batch_to_viewer(
    scenarios: list,
    n_agents: int = 3,
    n_steps: int = 8,
    n_reps: int = 5,
    viewer_template: str|None = None
):
    """Run multiple scenarios and generate viewer files."""
    
    results = {}
    
    for scenario_path in scenarios:
        print(f"\n\n{'='*70}")
        print(f"📁 Scenario: {scenario_path}")
        print('='*70)
        
        result = run_mc_to_viewer(
            scenario_path=scenario_path,
            n_agents=n_agents,
            n_steps=n_steps,
            n_reps=n_reps,
            open_browser=False,
            viewer_template=viewer_template
        )
        
        results[scenario_path] = result
    
    # Open all viewers
    print("\n\n🌐 Opening all viewers...")
    for scenario_path, result in results.items():
        webbrowser.open(f"file://{result['viewer_file']}")
    
    return results


# ============================================================
# 6. Simple Viewer Only (skip MC)
# ============================================================

def create_viewer_from_params(
    scenario_path: str,
    params: dict,
    seed: int = 42,
    viewer_template: str|None = None
) -> str:
    """Create a viewer directly from parameters (skip MC)."""
    
    print("🚀 Creating viewer from parameters")
    print("=" * 60)
    print(f"  Scenario: {scenario_path}")
    print(f"  Params: {params}")
    print("=" * 60)
    
    trace = generate_viewer_trace(
        scenario_path=scenario_path,
        params=params,
        seed=seed
    )
    
    viewer_file = inject_trace_into_viewer(trace, viewer_template=viewer_template)
    webbrowser.open(f"file://{viewer_file}")
    
    return viewer_file


# ============================================================
# 7. Main Entry Point
# ============================================================

if __name__ == "__main__":
    # Set the viewer template path explicitly
    VIEWER_TEMPLATE = "/Users/markfahim/Work/GRA GM/sandtable/report/viz/mission_viewer.html"
    
    # Check if it exists
    if Path(VIEWER_TEMPLATE).exists():
        print(f"✅ Found viewer template: {VIEWER_TEMPLATE}")
    else:
        print(f"⚠️  Viewer template not found at: {VIEWER_TEMPLATE}")
        print("   Will search for it...")
        VIEWER_TEMPLATE = None
    
    # Single scenario
    run_mc_to_viewer(
        scenario_path="scenarios/uc7_spoofed_advance.json",
        n_agents=5,
        n_steps=10,
        n_reps=8,
        open_browser=True,
        viewer_template=VIEWER_TEMPLATE
    )
    
    # Uncomment to run multiple scenarios:
    # run_batch_to_viewer([
    #     "scenarios/uc3_route_defilade.json",
    #     "scenarios/sc_span_control.json",
    #     "scenarios/uc5_sensor_swarm.json"
    # ])
    
    # Uncomment to create viewer from specific parameters (skip MC):
    # create_viewer_from_params(
    #     scenario_path="scenarios/uc3_route_defilade.json",
    #     params={"route_bias": 0.5, "comms_level": 0, "n_blue": 6, "tempo": 1.0},
    #     viewer_template=VIEWER_TEMPLATE
    # )