"""Deterministic map terrain and formation placement adapter."""

import numpy as np


class BuilderWorldAdapter:
    def __init__(self, compiled, state):
        self.compiled = compiled
        self.state = state

    def build(self, original, scn, rng):
        w = original(scn, rng)
        w.speed[:] = 1
        w.cover[:] = 0
        w.conceal[:] = 0
        yy, xx = np.mgrid[: w.speed.shape[0], : w.speed.shape[1]]
        xx = (xx + 0.5) * w.cell
        yy = (yy + 0.5) * w.cell
        ns = {n["id"]: n for n in self.compiled["config"]["map"]["nodes"]}
        for road in self.compiled["config"]["map"]["roads"]:
            a = ns[road["u"]]
            b = ns[road["v"]]
            vx = b["x"] - a["x"]
            vy = b["y"] - a["y"]
            t = np.clip(((xx - a["x"]) * vx + (yy - a["y"]) * vy) / (vx * vx + vy * vy), 0, 1)
            inside = np.hypot(xx - a["x"] - t * vx, yy - a["y"] - t * vy) <= road["width"] / 2
            w.speed[inside] = np.minimum(w.speed[inside], road["speed_mult"])
        if w.buildings is not None:
            w.speed[w.buildings] = 0.05
            w.cover[w.buildings] = 0.9
            w.conceal[w.buildings] = 0.9
        self.state["world"] = w
        self.state["goal_radius"] = scn.objective.goal_radius
        return w

    def place_entities(self, original, scn, rng):
        e = original(scn, rng)
        ids = np.flatnonzero(e.side == 0)
        spawn = np.array(self.compiled["summary"]["spawn"])
        e.x[ids] = spawn[:, 0]
        e.y[ids] = spawn[:, 1]
        s, _ = self.state["world"].route.project(e.x[ids], e.y[ids])
        _, _, h = self.state["world"].route.point_at(s)
        e.heading[ids] = h
        e.progress[ids] = s
        self.state["ent"] = e
        return e
