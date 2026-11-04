"""Normalize editor documents and validate physical input geometry."""

import math
from sandtable.routing.geometry import segment_intersects_box as segment_box
from .values import Invalid, number, option, point


class MapValidator:
    def normalize(self, raw, draft_mode=False):
        if not isinstance(raw, dict):
            raise Invalid("Map must be an object.")
        W = number(raw.get("width"), "World width", 500, 12000)
        H = number(raw.get("height"), "World height", 500, 8000)
        cell = number(raw.get("cell", 25), "Raster cell", 5, 100)
        if math.ceil(W / cell) * math.ceil(H / cell) > 600000:
            raise Invalid("Raster exceeds 600,000 cells; increase cell size.")
        if not isinstance(raw.get("nodes"), list) or len(raw["nodes"]) > 200:
            raise Invalid("Provide at most 200 road nodes.")

        def identity(x, name):
            if (
                not isinstance(x, str)
                or not x
                or len(x) > 60
                or (not all((t.isalnum() or t in "_-" for t in x)))
            ):
                raise Invalid(name + " must be a short alphanumeric identifier.")
            return x

        nodes = {}
        for n in raw["nodes"]:
            if not isinstance(n, dict):
                raise Invalid("Each road node must be an object.")
            key = identity(n.get("id"), "Node ID")
            p = point([n.get("x"), n.get("y")], key, W, H)
            if key in nodes:
                raise Invalid("Duplicate road node " + key)
            nodes[key] = dict(id=key, x=p[0], y=p[1])
        if not isinstance(raw.get("roads"), list) or len(raw["roads"]) > 300:
            raise Invalid("Provide at most 300 roads.")
        roads = []
        ids = set()
        pairs = set()
        for r in raw["roads"]:
            if not isinstance(r, dict):
                raise Invalid("Road must be an object.")
            key = identity(r.get("id"), "Road ID")
            u = r.get("u")
            v = r.get("v")
            if key in ids:
                raise Invalid("Duplicate road ID " + key)
            if u not in nodes or v not in nodes or u == v:
                raise Invalid(key + " must connect two distinct existing nodes.")
            pair = tuple(sorted([u, v]))
            if pair in pairs:
                raise Invalid("Duplicate connection " + str(pair))
            a = [nodes[u]["x"], nodes[u]["y"]]
            b = [nodes[v]["x"], nodes[v]["y"]]
            if math.dist(a, b) < 1:
                raise Invalid(key + " is shorter than one metre.")
            roads.append(
                dict(
                    id=key,
                    u=u,
                    v=v,
                    width=number(r.get("width", 100), key + " width", 8, 300),
                    speed_mult=number(r.get("speed_mult", 1), key + " trafficability", 0.1, 1),
                    exposure=number(r.get("exposure", 0.5), key + " exposure override", 0, 1),
                    exposure_mode=option(
                        r.get("exposure_mode", "manual"), key + " exposure mode", ["auto", "manual"]
                    ),
                )
            )
            ids.add(key)
            pairs.add(pair)
        if not roads and (not draft_mode):
            raise Invalid("Draw at least one road before validation.")
        bs = raw.get("buildings", [])
        if not isinstance(bs, list) or len(bs) > 100:
            raise Invalid("Provide at most 100 buildings.")
        buildings = []
        ids = set()
        for b in bs:
            if not isinstance(b, dict):
                raise Invalid("Each building must be an object.")
            key = identity(b.get("id"), "Building ID")
            box = b.get("box")
            if key in ids:
                raise Invalid("Duplicate building " + key)
            if not isinstance(box, list) or len(box) != 4:
                raise Invalid(key + " needs four box coordinates.")
            a = point(box[:2], key, W, H)
            z = point(box[2:], key, W, H)
            if z[0] - a[0] < 5 or z[1] - a[1] < 5:
                raise Invalid(key + " needs ordered corners at least 5 m apart.")
            buildings.append(dict(id=key, box=a + z))
            ids.add(key)
        for road in roads:
            a = [nodes[road["u"]]["x"], nodes[road["u"]]["y"]]
            b = [nodes[road["v"]]["x"], nodes[road["v"]]["y"]]
            for box in buildings:
                x0, y0, x1, y1 = box["box"]
                rb = [
                    math.floor(x0 / cell) * cell,
                    math.floor(y0 / cell) * cell,
                    math.ceil(x1 / cell) * cell,
                    math.ceil(y1 / cell) * cell,
                ]
                if not draft_mode and segment_box(a, b, rb, 3):
                    raise Invalid(
                        f"{road['id']} crosses building {box['id']} or its raster footprint. Move the road/building."
                    )
        red = []
        es = raw.get("red", [])
        if not isinstance(es, list) or len(es) > 30:
            raise Invalid("Provide at most 30 static Red sites.")
        ids = set()
        for e in es:
            if not isinstance(e, dict):
                raise Invalid("Each Red site must be an object.")
            key = identity(e.get("id"), "Red ID")
            p = point([e.get("x"), e.get("y")], key, W, H)
            if key in ids:
                raise Invalid("Duplicate Red ID " + key)
            if not draft_mode and any((segment_box(p, p, b["box"]) for b in buildings)):
                raise Invalid(key + " is inside a building.")
            red.append(
                dict(
                    id=key,
                    x=p[0],
                    y=p[1],
                    weapon_range=number(
                        e.get("weapon_range", 1000), key + " weapon range", 0, 5000
                    ),
                    sensor_range=number(
                        e.get("sensor_range", 2000), key + " sensor range", 0, 6000
                    ),
                    pk=number(e.get("pk", 0.008), key + " base probability", 0, 1),
                )
            )
            ids.add(key)
        start = point(raw.get("start"), "Start-area origin", W, H)
        goal = point(raw.get("goal"), "Goal", W, H)
        for title, p in [("Start", start), ("Goal", goal)]:
            if not draft_mode and any((segment_box(p, p, b["box"]) for b in buildings)):
                raise Invalid(title + " is inside a building.")
        mode = option(raw.get("route_mode", "auto"), "Route mode", ["auto", "manual"])
        bias = number(raw.get("route_bias", 0.5), "Route bias", 0, 1)
        mp = raw.get("manual_path", [])
        if (
            not isinstance(mp, list)
            or len(mp) > 200
            or any((not isinstance(x, str) or (not draft_mode and x not in nodes) for x in mp))
        ):
            raise Invalid("Manual path contains unknown road nodes.")
        return dict(
            route_algorithm=option(
                raw.get("route_algorithm", "dijkstra"), "Routing algorithm", ["dijkstra", "astar"]
            ),
            width=W,
            height=H,
            cell=cell,
            nodes=list(nodes.values()),
            roads=roads,
            buildings=buildings,
            red=red,
            start=start,
            goal=goal,
            goal_radius=number(raw.get("goal_radius", 150), "Goal radius", 5, min(W, H) / 3),
            route_mode=mode,
            manual_path=mp,
            route_bias=bias,
        )
