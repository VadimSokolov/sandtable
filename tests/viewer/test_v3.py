"""Focused contract tests: real engine, map topology, accounting, recovery and comparison fairness."""

import copy, json, math, sys, unittest
from pathlib import Path

from sandtable.mission_viewer.api import (
    Invalid,
    compile_config,
    default_config,
    route_graph,
    normalize_map,
    comparison_design,
    import_config,
    blank_config,
)
from sandtable.mission_viewer.simulation import run, Cancelled
from sandtable.mission_viewer.analytics import statistics_report


class ContractTests(unittest.TestCase):
    def config(self, duration=30):
        c = default_config()
        c["mission"]["duration"] = duration
        c["map"]["red"] = []
        return c

    def test_unfinished_map_can_be_saved_and_reopened(self):
        c = blank_config()
        restored = import_config(json.loads(json.dumps(c)))
        self.assertEqual(restored["map"]["roads"], [])
        with self.assertRaises(Invalid):
            compile_config(restored)
        c = default_config()
        c["mission"]["payload_kg"] = 6000
        restored = import_config(c)
        self.assertEqual(restored["mission"]["payload_kg"], 6000)
        with self.assertRaises(Invalid):
            compile_config(restored)

    def test_role_crew_capacity_and_mass_units(self):
        a = compile_config(self.config())
        s = a["summary"]
        self.assertEqual(
            (s["total_vehicles"], s["cargo_trucks"], s["escorts"], s["crew"], s["loaded_kg"]),
            (18, 12, 3, 15, 60000),
        )
        self.assertEqual(a["scenario"]["params"]["convoy"]["cargo_per_vehicle"], 5)
        c = self.config()
        c["mission"].update(crew_mode="crewed", escorts=0, layout="recovery")
        s = compile_config(c)["summary"]
        self.assertEqual(
            (s["total_vehicles"], s["cargo_trucks"], s["recovery"], s["crew"]), (15, 9, 3, 30)
        )

    def test_capacity_and_minimum_gap_rejected(self):
        for update in [
            dict(payload_kg=6000),
            dict(min_gap=6),
            dict(vehicles_per_unit=25),
            dict(console_transfer="successor", leader_loss="absorb"),
        ]:
            c = self.config()
            c["mission"].update(update)
            with self.assertRaises(Invalid):
                compile_config(c)

    def test_disconnected_and_building_route_rejected(self):
        c = self.config()
        c["map"]["route_mode"] = "auto"
        c["map"]["roads"] = [r for r in c["map"]["roads"] if r["u"] != "START"]
        with self.assertRaises(Invalid):
            compile_config(c)
        c = self.config()
        c["map"]["buildings"].append({"id": "CUT", "box": [200, 1450, 300, 1550]})
        with self.assertRaises(Invalid):
            compile_config(c)

    def test_crossings_and_t_junctions_become_connected(self):
        c = self.config()
        m = c["map"]
        m.update(
            nodes=[
                dict(id=k, x=x, y=y)
                for k, x, y in [
                    ("A", 100, 1000),
                    ("B", 2500, 1000),
                    ("C", 1500, 200),
                    ("D", 1500, 2200),
                ]
            ],
            roads=[dict(id="R1", u="A", v="B"), dict(id="R2", u="C", v="D")],
            buildings=[],
            red=[],
            start=[100, 1000],
            goal=[1500, 2200],
            route_mode="auto",
            manual_path=[],
        )
        a = compile_config(c)
        self.assertGreater(len(a["summary"]["route_nodes"]), 2)
        self.assertTrue(
            any(
                abs(n["x"] - 1500) < 1e-7 and abs(n["y"] - 1000) < 1e-7
                for n in a["summary"]["graph"]["nodes"]
            )
        )

    def test_outside_spawn_is_not_silently_clipped(self):
        c = self.config()
        c["mission"]["staging_m"] = 100
        with self.assertRaisesRegex(Invalid, "staging"):
            compile_config(c)

    def test_manual_and_auto_routes_differ_when_declared(self):
        c = self.config()
        direct = compile_config(c)["summary"]["route_length_m"]
        c["map"]["manual_path"] = ["START", "JUNCTION", "LOWER_W", "LOWER_E", "JOIN", "GOAL"]
        lower = compile_config(c)["summary"]["route_length_m"]
        self.assertGreater(lower, direct)
        c["map"].update(route_mode="auto", route_bias=0)
        self.assertAlmostEqual(compile_config(c)["summary"]["route_length_m"], direct)

    def test_fixed_cargo_reallocation_is_reproducible(self):
        c = self.config()
        c["mission"]["staging_m"] = 1400
        d = comparison_design(
            c, dict(parameter="vehicles_per_unit", values=[6], seeds=[0, 1], basis="same_cargo")
        )
        arm = d["arms"][1]["compiled"]
        self.assertEqual(arm["summary"]["loaded_kg"], 60000)
        self.assertEqual(arm["summary"]["cargo_trucks"], 15)
        self.assertEqual(arm["config"]["mission"]["payload_kg"], 4000)
        again = compile_config(arm["config"])
        self.assertEqual(again["scenario"], arm["scenario"])

    def test_fixed_fleet_rejects_fleet_size_and_transfer_confound(self):
        c = self.config()
        c["mission"]["staging_m"] = 1400
        with self.assertRaises(Invalid):
            comparison_design(
                c, dict(parameter="vehicles_per_unit", values=[6], seeds=[0], basis="same_fleet")
            )
        c["mission"]["console_transfer"] = "successor"
        with self.assertRaisesRegex(Invalid, "fixed console"):
            comparison_design(
                c, dict(parameter="leader_loss", values=["halt"], seeds=[0], basis="same_fleet")
            )

    def test_same_seed_reproduces_new_engine_frames(self):
        a = compile_config(self.config())
        x = run(a, 7)
        y = run(a, 7)
        self.assertEqual(x, y)
        self.assertEqual(x["frames"][0]["t"], 0)
        self.assertEqual(x["frames"][-1]["t"], x["outcome"]["mission_time"])
        for f in x["frames"]:
            self.assertAlmostEqual(
                f["cargo"]["loaded"],
                sum(f["cargo"][k] for k in ["delivered", "lost", "in_transit"]),
            )

    def test_end_snapshot_has_delivery_not_one_tick_stale(self):
        c = self.config(1400)
        x = run(compile_config(c), 0)
        self.assertEqual(x["outcome"]["cargo_success"], 1)
        self.assertEqual(x["frames"][-1]["cargo"]["delivered"], 60)
        self.assertEqual(x["frames"][-1]["cargo"]["delivered"], x["outcome"]["cargo_delivered"])

    def test_forced_loss_has_separate_leadership_and_console_recovery(self):
        c = self.config()
        c["mission"].update(
            diagnostic_loss_s=3, handoff_steps=2, console_transfer="successor", console_delay_s=2
        )
        x = run(compile_config(c), 0)
        events = {e["event"]: e["t"] for e in x["events"]}
        self.assertEqual(events["FORCED_DIAGNOSTIC_HEAD_LOSS"], 3)
        self.assertEqual(events["CREWED_LEADER_RESTORED"], 5)
        self.assertEqual(events["EXPERIMENTAL_CONSOLE_TRANSFER"], 7)
        self.assertEqual(x["outcome"]["cargo_lost"], 0)
        self.assertEqual(x["outcome"]["crew_lost"], 2)
        c["mission"]["console_transfer"] = "fixed"
        x = run(compile_config(c), 0)
        self.assertFalse(x["frames"][-1]["consoles"]["available"][0])
        self.assertGreaterEqual(x["frames"][-1]["heads"][0], 0)

    def test_cancel_checked_inside_actual_loop(self):
        with self.assertRaises(Cancelled):
            run(compile_config(self.config()), 0, cancel=lambda: True)

    def test_buildings_and_world_boundary_never_entered(self):
        c = default_config()
        c["mission"].update(duration=180, response="herringbone")
        x = run(compile_config(c), 3)
        for f in x["frames"]:
            for i, e in enumerate(x["entities"]):
                if e["side"] != 0:
                    continue
                self.assertGreaterEqual(f["x"][i], 0)
                self.assertLess(f["x"][i], c["map"]["width"])
                self.assertGreaterEqual(f["y"][i], 0)
                self.assertLess(f["y"][i], c["map"]["height"])
                for b in c["map"]["buildings"]:
                    x0, y0, x1, y1 = b["box"]
                    self.assertFalse(x0 <= f["x"][i] <= x1 and y0 <= f["y"][i] <= y1)

    def test_herringbone_does_not_release_independent_leader_halt(self):
        c = self.config(25)
        c["mission"].update(response="herringbone", leader_loss="halt", diagnostic_loss_s=3)
        x = run(compile_config(c), 0)
        self.assertGreater(sum(x["frames"][-1]["leader_hold"]), 0)
        self.assertEqual(x["outcome"]["ll_handoffs"], 0)

    def test_comparison_single_seed_does_not_invent_ci(self):
        keys = [
            "cargo_delivered",
            "delivered_frac",
            "cargo_lost",
            "cargo_in_transit",
            "crew_steps_at_risk",
            "crew_lost",
            "blue_losses",
            "mission_time",
            "cargo_success",
        ]
        out = {k: 1 for k in keys}
        rows = [
            dict(arm="baseline", seed=0, outcome=out),
            dict(arm="pace=8", seed=0, outcome={k: 2 for k in keys}),
        ]
        d = {"arms": [dict(name=n, compiled={"summary": {}}) for n in ["baseline", "pace=8"]]}
        s = statistics_report(rows, d)
        self.assertEqual(s[1]["metrics"]["cargo_delivered"]["paired_difference"], 1)
        self.assertIsNone(s[1]["metrics"]["cargo_delivered"]["paired_ci95"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
