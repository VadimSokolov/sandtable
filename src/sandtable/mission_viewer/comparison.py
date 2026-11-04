"""One-factor experiment design and fixed-cargo/fleet constraints."""

import copy
from sandtable.map_builder.values import Invalid, number, option
from .compiler import ScenarioCompiler

COMPARABLE = {
    "pace",
    "time_gap",
    "min_gap",
    "vehicles_per_unit",
    "units_per_serial",
    "serials",
    "escorts",
    "payload_kg",
    "response",
    "leader_loss",
    "comms",
}


class ComparisonDesigner:
    def __init__(self, compiler=None):
        self.compiler = compiler or ScenarioCompiler()

    def create(self, raw, design):
        if not isinstance(design, dict):
            raise Invalid("Comparison design must be an object.")
        parameter = option(design.get("parameter"), "Comparison parameter", sorted(COMPARABLE))
        values = design.get("values")
        seeds = design.get("seeds")
        basis = option(design.get("basis"), "Comparison basis", ["same_fleet", "same_cargo"])
        if not isinstance(values, list) or not 1 <= len(values) <= 5:
            raise Invalid("Provide 1-5 comparison values; baseline is added automatically.")
        if not isinstance(seeds, list) or not 1 <= len(seeds) <= 20:
            raise Invalid("Provide 1-20 seeds.")
        seeds = [number(x, "Seed", 0, 2**31 - 1, True) for x in seeds]
        if len(set(seeds)) != len(seeds):
            raise Invalid("Seeds must be distinct.")
        if (len(values) + 1) * len(seeds) > 60:
            raise Invalid("Limit the local comparison to 60 runs.")
        base = self.compiler.compile(raw)
        target = base["summary"]["loaded_kg"]
        arms = [dict(name="baseline", compiled=base)]
        if basis == "same_cargo" and parameter == "payload_kg":
            raise Invalid(
                "Fixed cargo would cancel a per-truck payload change. Use fixed fleet for that factor."
            )
        baselineval = base["config"]["mission"][parameter]
        seen = [baselineval]
        if (
            parameter == "leader_loss"
            and base["config"]["mission"]["console_transfer"] == "successor"
        ):
            raise Invalid(
                "Set fixed console ownership before comparing leader-loss policies; transfer is defined only for promote."
            )
        for value in values:
            if isinstance(value, bool):
                raise Invalid("Comparison values cannot be booleans.")
            if value in seen:
                continue
            c = copy.deepcopy(base["config"])
            c["mission"][parameter] = value
            if parameter == "leader_loss" and value != "promote":
                c["mission"]["console_transfer"] = "fixed"
            resolved = self.compiler.compile(c, target if basis == "same_cargo" else None)
            if basis == "same_fleet":
                keys = ["total_vehicles", "cargo_trucks", "escorts", "control", "recovery"]
                if any((resolved["summary"][k] != base["summary"][k] for k in keys)):
                    raise Invalid(
                        "Fixed-fleet comparison changes vehicle composition. Use fixed cargo for a fleet-size factor."
                    )
            arms.append(dict(name=parameter + "=" + str(value), compiled=resolved))
            seen.append(value)
        if len(arms) < 2:
            raise Invalid("Add at least one value different from baseline.")
        cost = sum(
            (
                a["compiled"]["summary"]["total_vehicles"] ** 2
                * a["compiled"]["config"]["mission"]["duration"]
                for a in arms
            )
        ) * len(seeds)
        if cost > 50000000:
            raise Invalid(
                "Comparison exceeds the local work budget; reduce fleet, duration, seeds or arms."
            )
        return dict(
            parameter=parameter,
            basis=basis,
            seeds=seeds,
            arms=arms,
            required_load_kg=target if basis == "same_cargo" else None,
            total_runs=len(arms) * len(seeds),
            warnings=[
                "Exploratory paired t intervals, unadjusted for multiple comparisons. Shared seeds do not preserve identical trajectories or request streams after divergence.",
                "Fixed fleet preserves vehicle composition; loaded cargo can change if payload is the factor."
                if basis == "same_fleet"
                else "Same initial loaded cargo in every arm; per-truck load is reallocated equally without exceeding capacity.",
            ],
        )
