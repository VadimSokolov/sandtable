"""Gilbert-Elliot bursty channel (CR-9): same mean drop rate, different burst structure."""
from __future__ import annotations

import numpy as np
import pytest

from sandtable.comms_ew import build_comms
from sandtable.scenario import load_scenario
from sandtable.sim import run_mission
from conftest import same_run

SCN = "scenarios/sc_span_control.json"
RUNGS = [1, 2, 3, 4, 5]


def _draws(level: int, channel: str, n: int = 200_000, burst: float = 4.0):
    scn = load_scenario(SCN).with_params(
        {"comms_level": level, "channel": channel, "ge_burst_len": burst})
    comms = build_comms(scn)
    rng = np.random.default_rng(12345)
    return comms, np.array([comms.delivered(rng) for _ in range(n)])


def _run_lengths(delivered: np.ndarray) -> list[int]:
    runs, cur = [], 0
    for ok in delivered:
        if not ok:
            cur += 1
        elif cur:
            runs.append(cur)
            cur = 0
    return runs


@pytest.mark.parametrize("level", RUNGS)
def test_ge_matches_ladder_mean_drop_rate(level):
    """The whole contrast rests on the means being equal, so assert it rung by rung."""
    comms, d = _draws(level, "gilbert_elliot")
    empirical = 1.0 - d.mean()
    assert empirical == pytest.approx(comms.p_drop, abs=0.01), (
        f"C{level}: GE drop {empirical:.4f} != ladder {comms.p_drop:.4f}")


@pytest.mark.parametrize("level", RUNGS)
def test_ge_bursts_are_longer_than_bernoulli(level):
    """Same mean, different structure: GE loss runs must be measurably longer."""
    _, d_b = _draws(level, "bernoulli")
    _, d_g = _draws(level, "gilbert_elliot")
    mb, mg = np.mean(_run_lengths(d_b)), np.mean(_run_lengths(d_g))
    assert mg > mb + 0.5, f"C{level}: GE burst {mg:.2f} not longer than Bernoulli {mb:.2f}"


def test_ge_burst_length_is_tunable():
    for burst in (2.0, 8.0):
        _, d = _draws(3, "gilbert_elliot", burst=burst)
        assert np.mean(_run_lengths(d)) == pytest.approx(burst, rel=0.15)


def test_bernoulli_default_is_byte_identical():
    """Opt-in discipline: with the channel unset, every scenario is bit-for-bit unchanged."""
    for path in ("scenarios/sc_span_control.json", "scenarios/uc3_route_defilade.json",
                 "scenarios/uc5_sensor_swarm.json", "scenarios/uc7_spoofed_advance.json"):
        scn = load_scenario(path)
        for seed in range(4):
            base = run_mission(scn, seed=seed)
            explicit = run_mission(scn, seed=seed, params={"channel": "bernoulli"})
            assert same_run(base, explicit), \
                f"{path} seed {seed}: explicit bernoulli diverged"


def test_both_channels_consume_one_draw_per_message():
    """Aligned RNG is what makes the two channels a paired comparison on a shared seed."""
    for channel in ("bernoulli", "gilbert_elliot"):
        scn = load_scenario(SCN).with_params({"comms_level": 3, "channel": channel})
        comms = build_comms(scn)
        rng = np.random.default_rng(7)
        for _ in range(500):
            comms.delivered(rng)
        # 500 messages must have consumed exactly 500 uniforms: a fresh generator
        # advanced 500 times has to sit at the identical state.
        ref = np.random.default_rng(7)
        ref.random(500)
        assert rng.bit_generator.state == ref.bit_generator.state, (
            f"{channel} did not draw exactly one uniform per message")
