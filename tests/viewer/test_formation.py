import sys
import unittest
from pathlib import Path

from sandtable.mission_viewer.api import default_config, formation_preview, compile_config
from sandtable.mission_viewer.simulation import run


class FormationTests(unittest.TestCase):
    def test_preview_matches_actual_initial_engine_entities(self):
        c = default_config()
        c["map"]["red"] = []
        c["mission"].update(duration=10, escorts=4)
        compiled = compile_config(c)
        preview = compiled["summary"]["formation"]
        actual = run(compiled, 0)
        for v, ent in zip(preview["vehicles"], actual["entities"]):
            for key in ["id", "role", "unit", "serial", "crew", "cargo_kg"]:
                self.assertEqual(v[key], ent[key])
            self.assertEqual(v["leader"], actual["frames"][0]["leader"][v["id"]])
            self.assertAlmostEqual(
                actual["frames"][0]["x"][v["id"]],
                compiled["summary"]["spawn"][v["id"]][0],
                places=3,
            )
            self.assertAlmostEqual(
                actual["frames"][0]["y"][v["id"]],
                compiled["summary"]["spawn"][v["id"]][1],
                places=3,
            )

    def test_map_independent_layout_and_crewed_console_exemption(self):
        m = default_config()["mission"]
        a = formation_preview(m)
        self.assertEqual(len(a["vehicles"]), 18)
        self.assertEqual(sum(v["console"] is not None for v in a["vehicles"]), 12)
        m.update(crew_mode="crewed", layout="recovery", escorts=0)
        b = formation_preview(m)
        self.assertTrue(all(v["console"] is None for v in b["vehicles"]))
        self.assertEqual(sum(v["role"] == 3 for v in b["vehicles"]), 3)
        self.assertEqual(b["physical_span_m"], b["centre_span_m"] + m["vehicle_length"])


if __name__ == "__main__":
    unittest.main()
