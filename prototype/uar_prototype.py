#!/usr/bin/env python3
"""
UAR-Mesh Python prototype
=========================
Purpose: test the CORE IDEA (confidence-aware path cost) on random networks
before touching ns-3. No packets, no radio simulation. Just graphs and shortest
paths, so it runs in seconds and every number is easy to explain.

What it does
  1. Builds a random wireless-like network (nodes in a square, links between
     nodes within radio range, each link has an ETX value).
  2. Gives every node a confidence score c in [0, 1].
  3. Computes routes under several cost functions:
        hop         : hop count only
        etx         : link quality only (the usual baseline)
        mult        : etx * (1 + alpha * (1 - c))        [UAR-Mesh, multiplicative]
        add         : etx + beta * (1 - c)               [UAR-Mesh, additive]
        threshold   : etx, but skip relays with c < c_min
        bottleneck  : maximize the lowest relay confidence, then minimize etx
  4. Reports metrics, averaged over many random trials with 95% CI.

Run:
    python3 uar_prototype.py
    python3 uar_prototype.py --nodes 100 --trials 50 --pattern clustered
    python3 uar_prototype.py --csv results.csv

Model assumptions (state these in the paper):
  - Nodes report their confidence honestly.
  - A relay with low confidence degrades the value of every packet through it.
    "Useful delivery" of a path = product of the confidences of its relays.
  - A relay is "low confidence" if c < LOW_CONF_THRESHOLD.
"""

import argparse
import csv
import heapq
import math
import random
import statistics

LOW_CONF_THRESHOLD = 0.5
INF = float("inf")
MODES = ["hop", "etx", "mult", "add", "threshold", "bottleneck"]


# ----------------------------------------------------------------------------
# Network and confidence generation
# ----------------------------------------------------------------------------
def build_network(n, area, radio_range, rng):
    """Random geometric graph. Link delivery probability falls with distance;
    ETX = 1 / (p_forward * p_reverse) with p_forward == p_reverse == p."""
    pos = [(rng.uniform(0, area), rng.uniform(0, area)) for _ in range(n)]
    links = {i: {} for i in range(n)}
    for i in range(n):
        for j in range(i + 1, n):
            d = math.dist(pos[i], pos[j])
            if d <= radio_range:
                p = 1.0 - 0.8 * (d / radio_range) ** 2  # 1.0 close, 0.2 at edge
                etx = 1.0 / (p * p)
                links[i][j] = etx
                links[j][i] = etx
    return pos, links


def assign_confidence(pos, low_fraction, pattern, area, rng):
    """Pick which nodes are low-confidence, then draw scores.
    pattern 'random'   : low nodes scattered anywhere
    pattern 'clustered': low nodes are the ones nearest a random point
                         (like a GPS-denied zone)"""
    n = len(pos)
    k = int(round(low_fraction * n))
    if pattern == "clustered":
        cx, cy = rng.uniform(0, area), rng.uniform(0, area)
        order = sorted(range(n), key=lambda i: math.dist(pos[i], (cx, cy)))
        low = set(order[:k])
    else:
        low = set(rng.sample(range(n), k))
    return [
        rng.uniform(0.05, 0.40) if i in low else rng.uniform(0.85, 1.00)
        for i in range(n)
    ]


# ----------------------------------------------------------------------------
# Cost functions and path computation
# ----------------------------------------------------------------------------
def edge_cost(mode, etx, c_v, is_dst, alpha, beta, c_min):
    """Cost of a hop that ENTERS node v. The destination is not a relay, so it
    is not penalised (the penalty would be the same for every path anyway)."""
    if mode == "hop":
        return 1.0
    if mode == "etx" or is_dst:
        return etx
    if mode == "mult":
        return etx * (1.0 + alpha * (1.0 - c_v))
    if mode == "add":
        return etx + beta * (1.0 - c_v)
    if mode == "threshold":
        return etx if c_v >= c_min else INF
    raise ValueError(mode)


def shortest_path(links, conf, src, dst, mode, alpha, beta, c_min):
    if mode == "bottleneck":
        return bottleneck_path(links, conf, src, dst)
    dist = {src: 0.0}
    prev = {}
    heap = [(0.0, src)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist.get(u, INF):
            continue
        if u == dst:
            break
        for v, etx in links[u].items():
            w = edge_cost(mode, etx, conf[v], v == dst, alpha, beta, c_min)
            if w == INF:
                continue
            nd = d + w
            if nd < dist.get(v, INF):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(heap, (nd, v))
    return rebuild(prev, src, dst) if dst in dist else None


def bottleneck_path(links, conf, src, dst):
    """Lexicographic Dijkstra: first maximise the worst relay confidence
    (rounded to 0.1 so tiny differences do not dominate), then minimise ETX."""
    start = (-1.0, 0.0)  # (negative bottleneck, etx); bottleneck 1.0 = no relays yet
    best = {src: start}
    prev = {}
    heap = [(start, src)]
    while heap:
        key, u = heapq.heappop(heap)
        if key > best.get(u, (INF, INF)):
            continue
        if u == dst:
            break
        for v, etx in links[u].items():
            relay_c = 1.0 if v == dst else round(conf[v], 1)
            nkey = (max(key[0], -relay_c), key[1] + etx)
            if nkey < best.get(v, (INF, INF)):
                best[v] = nkey
                prev[v] = u
                heapq.heappush(heap, (nkey, v))
    return rebuild(prev, src, dst) if dst in best else None


def rebuild(prev, src, dst):
    path = [dst]
    while path[-1] != src:
        path.append(prev[path[-1]])
    return path[::-1]


# ----------------------------------------------------------------------------
# Metrics
# ----------------------------------------------------------------------------
def path_metrics(path, conf, links):
    relays = path[1:-1]
    etx_total = sum(links[a][b] for a, b in zip(path, path[1:]))
    useful = 1.0
    for r in relays:
        useful *= conf[r]
    low = sum(1 for r in relays if conf[r] < LOW_CONF_THRESHOLD)
    return {"hops": len(path) - 1, "etx": etx_total, "useful": useful, "low": low}


def reachable(links, src, dst):
    seen, stack = {src}, [src]
    while stack:
        u = stack.pop()
        if u == dst:
            return True
        for v in links[u]:
            if v not in seen:
                seen.add(v)
                stack.append(v)
    return False


def run_trial(args, low_fraction, rng):
    pos, links = build_network(args.nodes, args.area, args.range, rng)
    conf = assign_confidence(pos, low_fraction, args.pattern, args.area, rng)

    # Choose flows that are connectable in the full graph. Same flows for all modes.
    flows = []
    tries = 0
    while len(flows) < args.flows and tries < 2000:
        tries += 1
        s, d = rng.sample(range(args.nodes), 2)
        if reachable(links, s, d):
            flows.append((s, d))
    if not flows:
        return None

    out = {}
    for mode in MODES:
        delivered = 0
        low_flows = 0
        useful_sum = 0.0
        etx_list, hop_list = [], []
        for s, d in flows:
            p = shortest_path(links, conf, s, d, mode, args.alpha, args.beta, args.cmin)
            if p is None:
                continue  # mode (e.g. threshold) disconnected this flow
            m = path_metrics(p, conf, links)
            delivered += 1
            low_flows += 1 if m["low"] > 0 else 0
            useful_sum += m["useful"]
            etx_list.append(m["etx"])
            hop_list.append(m["hops"])
        n = len(flows)
        out[mode] = {
            "delivered": delivered / n,
            "low_share": (low_flows / delivered) if delivered else 0.0,
            "useful": useful_sum / n,  # undelivered flows count as 0
            "etx": statistics.mean(etx_list) if etx_list else float("nan"),
            "hops": statistics.mean(hop_list) if hop_list else float("nan"),
        }
    return out


# ----------------------------------------------------------------------------
# Sanity check: with all confidence = 1, mult/add/bottleneck must equal etx
# ----------------------------------------------------------------------------
def sanity_check(args):
    rng = random.Random(123)
    pos, links = build_network(args.nodes, args.area, args.range, rng)
    conf = [1.0] * args.nodes
    checked = 0
    for _ in range(200):
        s, d = rng.sample(range(args.nodes), 2)
        if not reachable(links, s, d):
            continue
        base = shortest_path(links, conf, s, d, "etx", args.alpha, args.beta, args.cmin)
        base_cost = path_metrics(base, conf, links)["etx"]
        for mode in ("mult", "add", "threshold", "bottleneck"):
            p = shortest_path(links, conf, s, d, mode, args.alpha, args.beta, args.cmin)
            cost = path_metrics(p, conf, links)["etx"]
            assert abs(cost - base_cost) < 1e-9, (mode, s, d, cost, base_cost)
        checked += 1
    print(f"[sanity] c=1 everywhere: all variants match ETX baseline on {checked} flows. OK\n")


# ----------------------------------------------------------------------------
# Aggregation and reporting
# ----------------------------------------------------------------------------
def mean_ci(values):
    vals = [v for v in values if not math.isnan(v)]
    if not vals:
        return float("nan"), float("nan")
    if len(vals) < 2:
        return vals[0], 0.0
    return statistics.mean(vals), 1.96 * statistics.stdev(vals) / math.sqrt(len(vals))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--nodes", type=int, default=50)
    ap.add_argument("--area", type=float, default=1000.0)
    ap.add_argument("--range", type=float, default=250.0)
    ap.add_argument("--flows", type=int, default=20)
    ap.add_argument("--trials", type=int, default=30)
    ap.add_argument("--alpha", type=float, default=4.0, help="multiplicative penalty weight")
    ap.add_argument("--beta", type=float, default=5.0, help="additive penalty weight")
    ap.add_argument("--cmin", type=float, default=0.5, help="threshold variant cutoff")
    ap.add_argument("--pattern", choices=["random", "clustered"], default="random")
    ap.add_argument("--fractions", type=float, nargs="+", default=[0.0, 0.1, 0.25, 0.5])
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--csv", type=str, default=None)
    args = ap.parse_args()

    sanity_check(args)

    rows = []
    for frac in args.fractions:
        collected = {m: {k: [] for k in ("delivered", "low_share", "useful", "etx", "hops")} for m in MODES}
        for t in range(args.trials):
            rng = random.Random(args.seed * 100003 + t * 97 + int(frac * 1000))
            res = run_trial(args, frac, rng)
            if res is None:
                continue
            for m in MODES:
                for k, v in res[m].items():
                    collected[m][k].append(v)

        print(f"=== low-confidence fraction = {frac:.2f}  (nodes={args.nodes}, "
              f"pattern={args.pattern}, trials={args.trials}) ===")
        print(f"{'mode':<11}{'delivered':>11}{'low-relay%':>12}{'useful':>10}{'ETX':>9}{'hops':>7}")
        for m in MODES:
            d, _ = mean_ci(collected[m]["delivered"])
            ls, ls_ci = mean_ci(collected[m]["low_share"])
            u, u_ci = mean_ci(collected[m]["useful"])
            e, _ = mean_ci(collected[m]["etx"])
            h, _ = mean_ci(collected[m]["hops"])
            print(f"{m:<11}{d:>11.3f}{100*ls:>10.1f}%{u:>8.3f}+-{u_ci:.3f}{e:>7.2f}{h:>7.2f}")
            rows.append({"fraction": frac, "mode": m, "delivered": d,
                         "low_relay_share": ls, "low_relay_ci": ls_ci,
                         "useful": u, "useful_ci": u_ci, "etx": e, "hops": h})
        print()

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"Saved {args.csv}")


if __name__ == "__main__":
    main()
