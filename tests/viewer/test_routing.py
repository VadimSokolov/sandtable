"""Known-map routing contracts: exposure is a score, never a casualty forecast."""

import copy
import sys
import unittest
from pathlib import Path

from sandtable.mission_viewer.api import (
    default_config,
    normalize_map,
    route_graph,
    compile_config,
    import_config,
)
from sandtable.routing import RangeExposureModel, ThreatSite, ExposurePenaltyCost
from sandtable.street_graph import StreetEdge


def exposure(a, b, red, buildings, cell):
    return RangeExposureModel(
        [ThreatSite(r["x"], r["y"], r["weapon_range"], r["pk"]) for r in red],
        [b["box"] for b in buildings],
        cell,
    ).segment_score(a, b)


def cost(length, speed, score, bias):
    return ExposurePenaltyCost(bias)(
        StreetEdge("a", "b", length=length, speed_mult=speed, exposure=score)
    )


class RoutingTests(unittest.TestCase):
    def map(self):
        m = default_config()["map"]
        m.update(
            nodes=[
                dict(id=k, x=x, y=y)
                for k, x, y in [
                    ("S", 100, 1500),
                    ("G", 5500, 1500),
                    ("NW", 100, 2500),
                    ("NE", 5500, 2500),
                ]
            ],
            roads=[
                dict(id=k, u=u, v=v, width=100, speed_mult=1, exposure_mode="auto", exposure=0.5)
                for k, u, v in [
                    ("direct", "S", "G"),
                    ("west", "S", "NW"),
                    ("north", "NW", "NE"),
                    ("east", "NE", "G"),
                ]
            ],
            buildings=[],
            start=[100, 1500],
            goal=[5500, 1500],
            route_mode="auto",
            manual_path=[],
            route_bias=1,
            red=[dict(id="E", x=2800, y=1510, weapon_range=1800, sensor_range=2000, pk=0.01)],
        )
        return m

    def test_longer_lower_exposure_route_wins_and_algorithms_agree(self):
        m = self.map()
        m["route_bias"] = 0
        _, path, route, _ = route_graph(normalize_map(m))
        self.assertEqual(path, ["S", "G"])
        short = route.total_length
        m["route_bias"] = 1
        results = []
        for alg in ["dijkstra", "astar"]:
            m["route_algorithm"] = alg
            g, p, r, _ = route_graph(normalize_map(m))
            results.append(p)
            self.assertGreater(r.total_length, short)
        self.assertEqual(results[0], ["S", "NW", "NE", "G"])
        self.assertEqual(results[0], results[1])

    def test_building_screening_red_movement_and_range_gates(self):
        red = [dict(x=500, y=500, weapon_range=1000, pk=0.01)]
        a, b = [100, 100], [900, 100]
        open_score = exposure(a, b, red, [], 25)
        self.assertGreater(open_score, 0)
        self.assertEqual(exposure(a, b, red, [dict(box=[50, 200, 950, 300])], 25), 0)
        red[0]["x"] = 5000
        self.assertEqual(exposure(a, b, red, [], 25), 0)
        red[0].update(x=500, pk=0)
        self.assertEqual(exposure(a, b, red, [], 25), 0)

    def test_manual_override_roundtrip_and_old_drafts(self):
        c = default_config()
        c["map"] = self.map()
        r = c["map"]["roads"][0]
        r.update(exposure_mode="manual", exposure=0.123)
        normalized = import_config(c)
        self.assertEqual(normalized["map"]["roads"][0]["exposure"], 0.123)
        g, _, _, _ = route_graph(normalized["map"])
        self.assertEqual(g.edges[0].exposure, 0.123)
        del r["exposure_mode"]
        self.assertEqual(import_config(c)["map"]["roads"][0]["exposure_mode"], "manual")

    def test_no_red_auto_score_zero_cost_still_positive(self):
        m = self.map()
        m["red"] = []
        g, p, _, _ = route_graph(normalize_map(m))
        self.assertEqual(p, ["S", "G"])
        for e in g.edges:
            self.assertEqual(e.exposure, 0)
            self.assertGreater(cost(e.length, e.speed_mult, e.exposure, 1), 0)

    def test_score_is_bounded_and_reports_reproduce(self):
        c = default_config()
        c["map"] = self.map()
        c["map"]["red"] *= 1
        c["map"]["route_algorithm"] = "astar"
        a = compile_config(c)
        b = compile_config(a["config"])
        self.assertEqual(a["summary"]["routing"], b["summary"]["routing"])
        self.assertEqual(a["summary"]["route_nodes"], b["summary"]["route_nodes"])
        self.assertTrue(all(0 <= e["exposure_auto"] <= 1 for e in a["config"]["map"]["roads"]))

    def test_all_graph_costs_and_path_accumulation_are_auditable(self):
        c = default_config()
        c["map"] = self.map()
        a = compile_config(c)
        r = a["summary"]["routing"]
        self.assertEqual(len(r["all_edges"]), len(a["summary"]["graph"]["edges"]))
        self.assertTrue(any(not e["selected"] for e in r["all_edges"]))
        self.assertAlmostEqual(sum(e["cost"] for e in r["all_edges"] if e["selected"]), r["cost"])
        self.assertAlmostEqual(sum(e["cost"] for e in r["selected_edges"]), r["cost"])
        for e in r["all_edges"]:
            self.assertIn(e["road_id"], {q["id"] for q in c["map"]["roads"]})
            self.assertAlmostEqual(e["baseline_cost"] * e["penalty_multiplier"], e["cost"])


if __name__ == "__main__":
    unittest.main()
