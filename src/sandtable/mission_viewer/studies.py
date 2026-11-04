"""Immutable saved-study definitions and input identity."""

from pathlib import Path
import copy, json
from sandtable.map_builder.values import Invalid
from .api import default_config, compile_config, digest
from .paths import ViewerPaths

LIBRARY = ViewerPaths.discover().library
STUDY_ID = "sketch_12_900kg"
METRICS = [
    "cargo_delivered",
    "delivered_frac",
    "cargo_lost",
    "cargo_in_transit",
    "crew_steps_at_risk",
    "crew_lost",
    "blue_losses",
    "mission_time",
    "cargo_success",
    "leaderless_steps",
    "ll_handoffs",
    "v3_console_transfers",
    "v3_console_services",
    "v3_contact_occurred",
    "v3_head_loss_occurred",
    "v3_herringbone_episodes",
]


def build_definition():
    base = default_config()
    base["map"].update(
        route_mode="manual", manual_path=["START", "JUNCTION", "LOWER_W", "LOWER_E", "JOIN", "GOAL"]
    )
    base["mission"].update(
        units_per_serial=3,
        serials=1,
        escorts=3,
        capacity_kg=907.18474,
        pace=10,
        time_gap=4,
        min_gap=40,
        staging_m=1400,
        crew_mode="supervised",
        leader_loss="promote",
        handoff_steps=5,
        succession="manned_only",
        console_transfer="successor",
        console_delay_s=20,
        span_capacity=4,
        target_priority="control_first",
        diagnostic_loss_s=None,
        duration=1800,
        required_fraction=1,
    )
    scenarios = []
    for core in [5, 7]:
        for comms in [0, 3]:
            for response in ["continue", "halt", "herringbone"]:
                sid = "S" + str(len(scenarios) + 1)
                c = copy.deepcopy(base)
                c["name"] = f"{sid} · sketch · core {core} · {response} · C{comms}"
                c["mission"].update(
                    vehicles_per_unit=core,
                    payload_kg=900 if core == 5 else 600,
                    response=response,
                    comms=comms,
                    seed=0,
                )
                compiled = compile_config(c)
                scenarios.append(
                    dict(
                        id=sid,
                        title=c["name"],
                        configuration=compiled["config"],
                        configuration_hash=compiled["config_hash"],
                        factors=dict(core=core, response=response, comms=comms),
                    )
                )
    d = dict(
        id=STUDY_ID,
        title="Your sketch · 12 integrated scenarios",
        version=1,
        seeds=list(range(20)),
        required_load_kg=10800,
        capacity_kg=907.18474,
        scenarios=scenarios,
        metrics=METRICS,
        design="Full factorial: core vehicles 5/7 × Continue/Halt/Herringbone × C0/C3",
        scope=[
            "Fixed Your sketch map and lower-loop route; four static Red sites.",
            "Same initial loaded cargo and 15 onboard people in all arms; fleet size and cargo allocation change together.",
            "Natural combat only. Leader-loss, console transfer and contact are not guaranteed to trigger in every seed.",
            "Experimental Herringbone and promoted-head console transfer; #18 enables control-first only, not lane blocking or Red halt cost.",
            "Exploratory mean/paired 95% t intervals, unadjusted for multiple comparisons. Matched seeds need not preserve matched trajectories.",
        ],
    )
    d["design_hash"] = digest(d)
    return d


def verify_definition(d):
    if not isinstance(d, dict) or d.get("id") != STUDY_ID:
        raise Invalid("Unknown saved study.")
    if digest({k: v for k, v in d.items() if k != "design_hash"}) != d.get("design_hash"):
        raise Invalid("Saved study design hash does not match.")
    if d["seeds"] != list(range(20)) or len(d["scenarios"]) != 12:
        raise Invalid("Expected the declared 12 scenarios × 20 seeds.")
    arms = []
    map_hash = None
    route = None
    for a in d["scenarios"]:
        c = compile_config(a["configuration"])
        if c["config_hash"] != a["configuration_hash"]:
            raise Invalid("Saved scenario hash mismatch: " + a["id"])
        if abs(c["summary"]["loaded_kg"] - 10800) > 1e-07 or c["summary"]["crew"] != 15:
            raise Invalid("Study cargo/crew basis changed.")
        mh = digest(c["config"]["map"])
        if map_hash is not None and (mh != map_hash or c["summary"]["route_nodes"] != route):
            raise Invalid("Study maps/routes must match.")
        map_hash = mh
        route = c["summary"]["route_nodes"]
        arms.append(dict(name=a["id"], compiled=c))
    return arms


def install_definition():
    d = build_definition()
    folder = LIBRARY / STUDY_ID
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "manifest.json"
    if path.exists():
        existing = json.loads(path.read_text())
        verify_definition(existing)
        if existing["design_hash"] != d["design_hash"]:
            raise Invalid(
                "Existing saved definition differs; preserve it and create an explicit revision."
            )
    else:
        (folder / "configs").mkdir(exist_ok=True)
        for a in d["scenarios"]:
            (folder / "configs" / (a["id"] + ".json")).write_text(
                json.dumps(a["configuration"], indent=2) + "\n"
            )
        path.write_text(json.dumps(d, indent=2) + "\n")
    return d


def read_definition(sid, library=None):
    if sid != STUDY_ID:
        raise Invalid("Unknown saved study.")
    return json.loads(
        ((library or ViewerPaths.discover().library) / sid / "manifest.json").read_text()
    )


def describe(d):
    return {
        k: d[k]
        for k in [
            "id",
            "title",
            "version",
            "seeds",
            "required_load_kg",
            "capacity_kg",
            "design",
            "scope",
            "design_hash",
            "scenarios",
        ]
    }
