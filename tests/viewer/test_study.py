import copy
import sys
import unittest
from pathlib import Path

from sandtable.mission_viewer.api import Invalid, digest
from sandtable.mission_viewer.studies import build_definition, verify_definition
from sandtable.mission_viewer.analytics import summarize, diagnostics


class StudyTests(unittest.TestCase):
    def test_exact_factorial_same_map_cargo_and_capacity(self):
        d = build_definition()
        arms = verify_definition(d)
        self.assertEqual([a["id"] for a in d["scenarios"]], ["S" + str(i) for i in range(1, 13)])
        self.assertEqual(len({tuple(a["factors"].values()) for a in d["scenarios"]}), 12)
        self.assertEqual(len(arms) * len(d["seeds"]), 240)
        self.assertEqual({a["compiled"]["summary"]["loaded_kg"] for a in arms}, {10800})
        self.assertEqual(
            {a["compiled"]["config"]["mission"]["capacity_kg"] for a in arms}, {907.18474}
        )
        self.assertEqual({a["compiled"]["summary"]["crew"] for a in arms}, {15})
        self.assertEqual(
            {a["compiled"]["config"]["mission"]["payload_kg"] for a in arms}, {900, 600}
        )
        self.assertTrue(
            all(a["compiled"]["config"]["mission"]["diagnostic_loss_s"] is None for a in arms)
        )

    def test_tampered_manifest_is_rejected(self):
        d = build_definition()
        d["scenarios"][0]["configuration"]["mission"]["payload_kg"] = 1
        with self.assertRaises(Invalid):
            verify_definition(d)
        d["design_hash"] = digest({k: v for k, v in d.items() if k != "design_hash"})
        with self.assertRaises(Invalid):
            verify_definition(d)

    def test_interaction_uses_matched_seeds_not_arm_means(self):
        d = build_definition()
        rows = []
        for a in d["scenarios"]:
            for seed in [0, 1]:
                # Halt adds 2 at C0, 7 at C3; interaction is +5 per seed.
                val = seed * 100 + (
                    2 + 5 * (a["factors"]["comms"] == 3)
                    if a["factors"]["response"] == "halt"
                    else 0
                )
                rows.append(
                    dict(
                        arm=a["id"],
                        seed=seed,
                        outcome=dict(
                            cargo_delivered=val,
                            crew_steps_at_risk=val,
                            blue_losses=val,
                            cargo_success=0,
                            mission_time=1800,
                        ),
                    )
                )
        r = summarize(list(reversed(rows)), d)
        x = next(a for a in r["interactions"] if a["core"] == 5 and a["response"] == "halt")[
            "metrics"
        ]["cargo_delivered"]
        self.assertEqual((x["n"], x["mean"], x["ci95"]), (2, 5, [5, 5]))
        self.assertEqual(r["scenarios"][0]["time_to_full_delivery"]["n"], 0)
        self.assertIsNone(r["scenarios"][0]["time_to_full_delivery"]["mean"])

    def test_diagnostics_do_not_assume_mechanisms_fired(self):
        artifact = dict(
            outcome=dict(first_leader_loss_step=None, convoy_contact_count=0),
            events=[],
            frames=[dict(consoles=None)],
        )
        self.assertEqual(
            diagnostics(artifact),
            dict(
                v3_console_transfers=0,
                v3_console_services=0,
                v3_head_loss_occurred=0,
                v3_contact_occurred=0,
            ),
        )


if __name__ == "__main__":
    unittest.main()
