"""Two graph readings of a formation, and the literature's warning that they disagree.

Every formation reading in this project so far has been geometric: a distance to a commanded
station, or the spread of the living force about its own centroid. This module reads the same
positions as a COMMUNICATION GRAPH and scores its resilience, which the resilient-consensus
literature says is a different question from how connected it is.

Two numbers are computed on that graph and they are chosen to disagree:

* Algebraic connectivity, the second-smallest Laplacian eigenvalue. This is the metric an earlier
  idea in this project's literature notes proposed for mapping the degradation ladder onto a
  formation. It is a global, continuous measure of how well knit a graph is.
* Vertex connectivity, the size of the smallest set of vehicles whose loss disconnects the rest.
  By Menger's theorem this is the number of internally vertex-disjoint paths between the worst
  pair, which is exactly the quantity the resilient-consensus results are stated in: Sundaram and
  Hadjicostis show that 2f+1 vertex-disjoint paths suffice to tolerate f compromised agents and
  that 2f provably do not, so a graph of vertex connectivity kappa carries a tolerance of
  floor((kappa - 1) / 2).

LeBlanc and colleagues state plainly that connectivity is not adequate to characterise resilient
consensus, and a path graph is the standing counterexample: its vertex connectivity is 1 however
long it is, while its algebraic connectivity falls steadily with length. A formation tuned on the
eigenvalue is not thereby robust to a compromised vehicle, and the disagreement is the point.

SCOPE. These theorems are about CONSENSUS among agents. SandTable's blue vehicles do not run a
consensus protocol; they pursue targets independently. What is scored here is therefore the
communication topology's resilience and not a proven property of the mission. Nothing in this module
licenses the sentence "the formation tolerates f compromised agents".
"""
from __future__ import annotations

import numpy as np


def comms_graph(x: np.ndarray, y: np.ndarray, radius: float) -> np.ndarray:
    """Adjacency of the disc graph at `radius`: two vehicles are linked if they are close enough.

    A disc graph is the weakest honest model of a peer link. It has no terrain in it and no fading,
    so it describes the geometry the formation commands rather than the radio it would get.
    """
    d = np.hypot(x[:, None] - x[None, :], y[:, None] - y[None, :])
    a = (d <= radius).astype(np.int8)
    np.fill_diagonal(a, 0)
    return a


def algebraic_connectivity(adj: np.ndarray) -> float:
    """Second-smallest eigenvalue of the Laplacian. Zero when the graph is disconnected."""
    n = adj.shape[0]
    if n < 2:
        return 0.0
    lap = np.diag(adj.sum(axis=1).astype(float)) - adj.astype(float)
    w = np.linalg.eigvalsh(lap)
    return float(max(w[1], 0.0))


def _max_vertex_disjoint(adj: np.ndarray, s: int, t: int) -> int:
    """Internally vertex-disjoint s-to-t paths, by max flow on the node-split digraph.

    Each vertex v becomes v_in -> v_out with capacity one, so a unit of flow may pass through it
    once; s and t are given unbounded capacity because a path is allowed to use its own endpoints.
    Edges become unbounded arcs between the split halves. Menger's theorem makes the resulting max
    flow equal to the smallest set of OTHER vertices whose removal separates s from t.
    """
    n = adj.shape[0]
    big = n + 1
    cap = [[0] * (2 * n) for _ in range(2 * n)]

    def vin(v):
        return 2 * v

    def vout(v):
        return 2 * v + 1

    for v in range(n):
        cap[vin(v)][vout(v)] = big if v in (s, t) else 1
    for u in range(n):
        for v in range(n):
            if adj[u, v]:
                cap[vout(u)][vin(v)] = big

    src, snk, flow = vout(s), vin(t), 0
    while True:
        # Breadth-first augmenting path, which makes this Edmonds-Karp and bounds the work.
        prev = [-1] * (2 * n)
        prev[src] = src
        queue = [src]
        while queue and prev[snk] < 0:
            nxt = []
            for u in queue:
                for v in range(2 * n):
                    if prev[v] < 0 and cap[u][v] > 0:
                        prev[v] = u
                        nxt.append(v)
            queue = nxt
        if prev[snk] < 0:
            return flow
        # The bottleneck along the path, then push it.
        v, bottleneck = snk, big
        while v != src:
            bottleneck = min(bottleneck, cap[prev[v]][v])
            v = prev[v]
        v = snk
        while v != src:
            cap[prev[v]][v] -= bottleneck
            cap[v][prev[v]] += bottleneck
            v = prev[v]
        flow += bottleneck


def _vertex_connectivity_exact(adj: np.ndarray) -> int:
    """Smallest number of vehicles whose loss disconnects the rest. Exact, not a bound.

    A complete graph has no non-adjacent pair to separate and is conventionally n-1 connected. Any
    other graph's connectivity is the minimum over non-adjacent pairs, which is the textbook
    characterisation and is affordable here because a formation is at most a few dozen vehicles.
    """
    n = adj.shape[0]
    if n < 2:
        return 0
    if int(adj.sum()) == n * (n - 1):
        return n - 1
    best = n - 1
    for s in range(n):
        for t in range(s + 1, n):
            if adj[s, t]:
                continue
            best = min(best, _max_vertex_disjoint(adj, s, t))
            if best == 0:
                return 0
    return int(best)


def vertex_connectivity(adj: np.ndarray) -> int:
    """The same number, computed by whichever implementation is available.

    NetworkX gets there about six times faster on the graph sizes this project uses, because it
    makes far fewer max-flow calls than the textbook minimum-over-non-adjacent-pairs form above.
    The textbook form is kept rather than deleted: it is the independent implementation the tests
    check the fast path against, and it is the fallback where NetworkX is absent. A guard that
    cannot be checked against anything is not a guard.
    """
    n = adj.shape[0]
    if n < 2:
        return 0
    try:
        import networkx as nx
    except ImportError:
        return _vertex_connectivity_exact(adj)
    return int(nx.node_connectivity(nx.from_numpy_array(np.asarray(adj))))


def tolerated_faults(kappa: int) -> int:
    """The f in the 2f+1 result: how many compromised agents the TOPOLOGY could carry.

    Stated about the graph and not about the mission, because these vehicles run no consensus.
    """
    return max(0, (int(kappa) - 1) // 2)


def score(x: np.ndarray, y: np.ndarray, radius: float) -> dict:
    """Both readings of one set of positions, plus the fault count the theorem attaches to one."""
    adj = comms_graph(x, y, radius)
    kappa = vertex_connectivity(adj)
    return {"fiedler": algebraic_connectivity(adj),
            "kappa": float(kappa),
            "faults": float(tolerated_faults(kappa)),
            "disconnected": 1.0 if kappa == 0 else 0.0}
