"""Connect crossings and projected anchors; retain each segment's source road."""

from dataclasses import dataclass
from sandtable.street_graph import StreetGraph
from sandtable.routing import RangeExposureModel
from sandtable.routing.geometry import project_point as projection
from .values import Invalid


@dataclass
class GraphBuild:
    graph: StreetGraph
    anchors: dict
    expansions: dict
    source_roads: tuple
    warnings: list


class RoadGraphBuilder:
    def __init__(self, model_factory=None):
        self.model_factory = model_factory or RangeExposureModel.from_map

    def build(self, m):
        """Split every crossing/T-junction, as well as projected start and goal anchors."""
        ns = {n["id"]: n for n in m["nodes"]}
        roads = m["roads"]
        pts = {}
        cuts = {r["id"]: [(0, r["u"]), (1, r["v"])] for r in roads}
        warnings = []

        def pos(k):
            return [ns[k]["x"], ns[k]["y"]]

        def at(p):
            key = (round(p[0], 6), round(p[1], 6))
            if key in pts:
                return pts[key]
            nid = "X" + str(len(pts) + 1)
            while nid in ns:
                nid += "x"
            ns[nid] = dict(id=nid, x=p[0], y=p[1])
            pts[key] = nid
            return nid

        for n in ns.values():
            pts[round(n["x"], 6), round(n["y"], 6)] = n["id"]
        for i, r in enumerate(roads):
            a, b = (pos(r["u"]), pos(r["v"]))
            v = [b[0] - a[0], b[1] - a[1]]
            for q in roads[i + 1 :]:
                c, d = (pos(q["u"]), pos(q["v"]))
                w = [d[0] - c[0], d[1] - c[1]]
                cross = v[0] * w[1] - v[1] * w[0]
                if abs(cross) < 1e-08:
                    # Check interval overlap symmetrically; a long segment may contain
                    # an earlier short segment without either long endpoint lying in it.
                    if abs((c[0] - a[0]) * v[1] - (c[1] - a[1]) * v[0]) < 1e-5:
                        denominator = v[0] * v[0] + v[1] * v[1]
                        t0 = ((c[0] - a[0]) * v[0] + (c[1] - a[1]) * v[1]) / denominator
                        t1 = ((d[0] - a[0]) * v[0] + (d[1] - a[1]) * v[1]) / denominator
                        if min(1.0, max(t0, t1)) - max(0.0, min(t0, t1)) > 1e-7:
                            raise Invalid(
                                "Overlapping collinear roads; split/delete the duplicate segment."
                            )
                    continue
                t = ((c[0] - a[0]) * w[1] - (c[1] - a[1]) * w[0]) / cross
                u = ((c[0] - a[0]) * v[1] - (c[1] - a[1]) * v[0]) / cross
                if -1e-08 <= t <= 1 + 1e-08 and -1e-08 <= u <= 1 + 1e-08:
                    nid = at([a[0] + t * v[0], a[1] + t * v[1]])
                    cuts[r["id"]].append((max(0, min(1, t)), nid))
                    cuts[q["id"]].append((max(0, min(1, u)), nid))
        anchors = {}
        for kind in ["start", "goal"]:
            candidates = []
            for r in roads:
                t, p, dist = projection(m[kind], pos(r["u"]), pos(r["v"]))
                candidates.append((dist, r["id"], t, p, r))
            dist, rid, t, p, r = min(candidates, key=lambda x: x[0])
            if dist > max(5, r["width"] / 2):
                raise Invalid(kind.title() + " must be on a road (within its half-width).")
            if dist > 1e-05:
                warnings.append(f"{kind.title()} projected {dist:.2f} m to road {rid}.")
            nid = at(p)
            anchors[kind] = nid
            cuts[rid].append((t, nid))
        edges = []
        expansions = {}
        sources = []
        exposure_model = self.model_factory(m)
        for r in roads:
            cs = sorted(cuts[r["id"]])
            unique = []
            for t, key in cs:
                if not unique or abs(t - unique[-1][0]) > 1e-07:
                    unique.append((t, key))
            expansions[r["id"]] = [k for t, k in unique]
            for (_, u), (_, v) in zip(unique, unique[1:]):
                if u == v:
                    continue
                score = (
                    exposure_model.score([pos(u), pos(v)])
                    if r["exposure_mode"] == "auto"
                    else r["exposure"]
                )
                edges.append(
                    dict(u=u, v=v, width=r["width"], speed_mult=r["speed_mult"], exposure=score)
                )
                sources.append(r["id"])
        graph = StreetGraph.from_dict(dict(nodes=list(ns.values()), edges=edges))
        return GraphBuild(graph, anchors, expansions, tuple(sources), warnings)
