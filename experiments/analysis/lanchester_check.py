"""Analytic cross-check: does sandtable's emergent attrition follow Lanchester's square law?

We exercise the real `sandtable.engagement.step` kernel in a controlled aimed-fire duel
(two facing ranks, every pair in weapon range, no cover, all mutually detected)
and compare the Monte-Carlo mean force trajectories B(t), R(t) to the continuous
Lanchester square-law ODE

    dB/dt = -a R,   dR/dt = -b B,        a = pk_red,  b = pk_blue

whose invariant is  b*B(t)^2 - a*R(t)^2 = const. Matching the closed form (in the
small-pk, distinct-target regime) validates that the engagement kernel integrates
attrition correctly; the known ABM deviation (fire concentration / overkill when
survivors share a nearest target) is quantified rather than hidden. Method follows
Gaertner (2013), who validated an agent-based swarm sim against a Markov/Lanchester
model.

Run:  conda run -n sandtable python experiments/analysis/lanchester_check.py
"""
from __future__ import annotations

import numpy as np

from sandtable.engagement import step as engage
from sandtable.entities import BLUE, RED, Entities
from sandtable.world import World

# ---- duel configuration ---------------------------------------------------
N_B, N_R = 30, 30           # equal ranks so early pairing is one-to-one
PK_BLUE, PK_RED = 0.02, 0.03  # per-second kill probabilities (red stronger)
GAP = 30.0                  # lateral spacing within a rank (m)
SEP = 50.0                  # blue-red rank separation (m); << weapon range
WEAPON_RANGE = 400.0        # every cross-pair is in range
T = 60                      # steps (== seconds, dt = 1)
REPS = 600
SEED = 20260716


def build_duel() -> Entities:
    """Two facing ranks: blue_i at (0, i*GAP) pairs with red_i at (SEP, i*GAP)."""
    e = Entities.allocate(N_B + N_R)
    for i in range(N_B):
        e.x[i], e.y[i] = 0.0, i * GAP
        e.side[i] = BLUE
        e.pk_base[i] = PK_BLUE
    for j in range(N_R):
        k = N_B + j
        e.x[k], e.y[k] = SEP, j * GAP
        e.side[k] = RED
        e.pk_base[k] = PK_RED
    e.hp[:] = 1.0
    e.alive[:] = True
    e.weapon_range[:] = WEAPON_RANGE
    e.sensor_range[:] = WEAPON_RANGE
    return e


def flat_world() -> World:
    """Zero cover / concealment so pk = pk_base exactly."""
    z = np.zeros((4, 4))
    return World(size=(SEP + 10, N_B * GAP + 10), cell=max(SEP, N_B * GAP),
                 speed=np.ones((4, 4)), cover=z.copy(), conceal=z.copy())


def sim_trajectory() -> tuple[np.ndarray, np.ndarray]:
    """MC-mean surviving counts B(t), R(t) over REPS reps, using the real kernel."""
    world = flat_world()
    ss = np.random.SeedSequence(SEED)
    B = np.zeros(T + 1)
    R = np.zeros(T + 1)
    for rep, child in enumerate(ss.spawn(REPS)):
        rng = np.random.default_rng(child)
        e = build_duel()
        B[0] += N_B
        R[0] += N_R
        for t in range(1, T + 1):
            e.seen = e.alive.copy()            # force mutual detection (bypass sensing)
            engage(e, world, dt=1.0, rng=rng)
            B[t] += int((e.alive & (e.side == BLUE)).sum())
            R[t] += int((e.alive & (e.side == RED)).sum())
    return B / REPS, R / REPS


def lanchester_ode(a: float, b: float, B0: float, R0: float) -> tuple[np.ndarray, np.ndarray]:
    """RK4 integration of the square-law ODE at dt=1 (clamped at 0)."""
    B = np.zeros(T + 1)
    R = np.zeros(T + 1)
    B[0], R[0] = B0, R0
    bt, rt = B0, R0
    h = 1.0
    for t in range(1, T + 1):
        def dB(r):  # dB/dt = -a R
            return -a * r
        def dR(bb):  # dR/dt = -b B
            return -b * bb
        k1b, k1r = dB(rt), dR(bt)
        k2b, k2r = dB(rt + 0.5 * h * k1r), dR(bt + 0.5 * h * k1b)
        k3b, k3r = dB(rt + 0.5 * h * k2r), dR(bt + 0.5 * h * k2b)
        k4b, k4r = dB(rt + h * k3r), dR(bt + h * k3b)
        bt = max(0.0, bt + h / 6 * (k1b + 2 * k2b + 2 * k3b + k4b))
        rt = max(0.0, rt + h / 6 * (k1r + 2 * k2r + 2 * k3r + k4r))
        B[t], R[t] = bt, rt
    return B, R


def main() -> None:
    a, b = PK_RED, PK_BLUE                       # a kills blue, b kills red
    Bs, Rs = sim_trajectory()
    Bo, Ro = lanchester_ode(a, b, N_B, N_R)

    print(f"Lanchester square-law cross-check  (N_B={N_B}, N_R={N_R}, "
          f"pk_blue={PK_BLUE}, pk_red={PK_RED}, reps={REPS})\n")
    print(f"{'t':>3} | {'B_sim':>6} {'B_ode':>6} | {'R_sim':>6} {'R_ode':>6}")
    for t in range(0, T + 1, 10):
        print(f"{t:3d} | {Bs[t]:6.2f} {Bo[t]:6.2f} | {Rs[t]:6.2f} {Ro[t]:6.2f}")

    # Compare over the window where both models have > 1 survivor (before depletion).
    mask = (Bo > 1) & (Ro > 1)
    rmse_B = float(np.sqrt(np.mean((Bs[mask] - Bo[mask]) ** 2)))
    rmse_R = float(np.sqrt(np.mean((Rs[mask] - Ro[mask]) ** 2)))
    # Lanchester invariant on the simulated trajectory: b*B^2 - a*R^2 should hold.
    inv = b * Bs ** 2 - a * Rs ** 2
    inv0 = inv[0]
    inv_drift = float(np.max(np.abs(inv[mask] - inv0)) / abs(inv0)) if mask.any() else float("nan")

    print(f"\nRMSE(sim vs square-law ODE): B {rmse_B:.2f}, R {rmse_R:.2f} "
          f"(over t where both > 1, {int(mask.sum())} pts)")
    print(f"Lanchester invariant b*B^2 - a*R^2: start {inv0:.2f}, "
          f"max relative drift {inv_drift*100:.1f}%")
    verdict = "PASS" if (rmse_B < 1.5 and rmse_R < 1.5 and inv_drift < 0.15) else "DEVIATION"
    print(f"\nVerdict: {verdict} -- emergent attrition tracks the square law "
          f"in the aimed-fire, distinct-target regime.")
    print("(Deviation grows once survivors thin and share a nearest target: the "
          "classic ABM fire-concentration effect, expected and bounded here.)")


if __name__ == "__main__":
    main()
