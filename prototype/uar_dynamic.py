#!/usr/bin/env python3
"""
uar_dynamic.py : Dynamic Confidence-Aware routing prototype (v2)
================================================================
Research question this script is built around:

    Can dynamically estimated node confidence improve packet-delivery
    reliability of OLSR-style routing WITHOUT unacceptable increases in path
    length, delay and route instability?

(Control overhead is an ANALYTICAL ESTIMATE here, not a measurement. Real
values come from ns-3.)

What is simulated, second by second (default 300 s):
  1. Nodes move (random waypoint). Links exist within radio range.
  2. A chosen fraction of nodes are "fragile". Their TRUE forwarding
     reliability r_i(t) drops and recovers over time. A degraded relay really
     does drop packets (this is what makes PDR respond to the idea).
  3. Every node estimates its own confidence from observed forwarding success:
         C_i <- lambda * C_i + (1 - lambda) * F_i      (F_i = successes/attempts this second)
     Nodes that get no traffic observations drift slowly back toward 1
     ("recovery"), otherwise an avoided node could never be re-tested.
  4. Every ROUTE_INTERVAL seconds, routes are recomputed from the advertised
     (therefore slightly stale) confidences using the selected cost function.
  5. Hysteresis H: a working route is only replaced if the new route is cheaper
     than the current one by more than a factor H.
  6. One packet per flow per second is pushed through the current route. It is
     lost if a link is missing, a link attempt fails, or a relay fails to forward.

Routing modes (cost of entering a relay v; destination is never penalised):
  olsr          base                              baseline, confidence ignored
  add           base + alpha * (1 - C_v)
  mult          base * (1 + alpha * (1 - C_v))
  threshold     base + alpha   if C_v < thr       (a soft penalty, NOT exclusion)
  add-adaptive  additive, alpha grows with the fraction of known low-confidence nodes
  base = 1 (hop count, like stock ns-3 OLSR) or ETX with --base etx

Common random numbers: for a given seed, every configuration sees the SAME
movement, the SAME reliability trajectory and the SAME packet random draws, so
differences between configurations are not noise from different scenarios.

Outputs:
  * table of all configurations with deltas against the olsr baseline
  * flags:  A = meets the acceptability criteria,  P = on the Pareto frontier
            of (PDR up, delay down)
  * raw per-seed CSV and optional plots (--plot DIR)

Acceptability criteria (CHOOSE AND JUSTIFY THESE BEFORE LOOKING AT RESULTS;
the defaults are placeholders): relative PDR gain >= --min-gain, delay increase
<= --max-delay-inc, hop increase <= --max-hop-inc.

Examples
    python3 uar_dynamic.py --trials 20
    python3 uar_dynamic.py --fragile 0.5 --speed 15 --trials 20 --csv raw.csv --plot figs
    python3 uar_dynamic.py --alphas 1 2 4 8 16 --hyst 0 0.05 0.1 0.15
"""

import argparse
import csv
import heapq
import math
import os
import random
import statistics

INF = float("inf")
LOW = 0.5  # a node is "low confidence" / "really bad" below this


# ----------------------------------------------------------------------------
# Scenario: everything that must be identical across configurations of one seed
# ----------------------------------------------------------------------------
class Scenario:
    pass


def build_scenario(args, seed):
    rng = random.Random(seed)
    n, T, area, R = args.nodes, args.time, args.area, args.range
    pos = [[rng.uniform(0, area), rng.uniform(0, area)] for _ in range(n)]
    tgt = [[rng.uniform(0, area), rng.uniform(0, area)] for _ in range(n)]
    spd = [rng.uniform(1.0, max(args.speed, 1.5)) for _ in range(n)]

    fragile = set(rng.sample(range(n), int(round(args.fragile * n))))
    r = [0.98] * n
    target = [0.98] * n
    degraded = [False] * n
    p_deg = min(1.0, 0.04 * args.volatility)
    p_rec = min(1.0, 0.02 * args.volatility)

    graphs, rel = [], []
    for _ in range(T):
        if args.speed > 0:
            for i in range(n):
                dx, dy = tgt[i][0] - pos[i][0], tgt[i][1] - pos[i][1]
                dist = math.hypot(dx, dy)
                if dist <= spd[i]:
                    pos[i] = tgt[i][:]
                    tgt[i] = [rng.uniform(0, area), rng.uniform(0, area)]
                    spd[i] = rng.uniform(1.0, max(args.speed, 1.5))
                else:
                    pos[i][0] += dx / dist * spd[i]
                    pos[i][1] += dy / dist * spd[i]

        g = [dict() for _ in range(n)]
        for i in range(n):
            xi, yi = pos[i]
            for j in range(i + 1, n):
                d = math.hypot(xi - pos[j][0], yi - pos[j][1])
                if d <= R:
                    p = 1.0 - 0.8 * (d / R) ** 2        # single-try delivery probability
                    q = 1.0 - (1.0 - p) ** 3            # delivery with 3 MAC attempts
                    link = (p, 1.0 / (p * p), q)        # (p, ETX, q)
                    g[i][j] = link
                    g[j][i] = link
        graphs.append(g)

        for i in range(n):
            if i in fragile:
                if not degraded[i] and rng.random() < p_deg:
                    degraded[i] = True
                    target[i] = rng.uniform(0.10, 0.50)
                elif degraded[i] and rng.random() < p_rec:
                    degraded[i] = False
                    target[i] = 0.98
            r[i] += 0.3 * (target[i] - r[i])
        rel.append(r[:])

    # flows: random pairs that are connected at t = 0
    flows, tries = [], 0
    while len(flows) < args.flows and tries < 5000:
        tries += 1
        s, d = rng.sample(range(n), 2)
        if (s, d) not in flows and connected(graphs[0], s, d):
            flows.append((s, d))

    sc = Scenario()
    sc.n, sc.T, sc.graphs, sc.rel, sc.flows = n, T, graphs, rel, flows
    sc.u = [[[rng.random() for _ in range(64)] for _ in flows] for _ in range(T)]
    return sc


def connected(g, s, d):
    seen, stack = {s}, [s]
    while stack:
        u = stack.pop()
        if u == d:
            return True
        for v in g[u]:
            if v not in seen:
                seen.add(v)
                stack.append(v)
    return False


# ----------------------------------------------------------------------------
# Cost functions and routing
# ----------------------------------------------------------------------------
def edge_w(mode, base, c, is_dst, a, args):
    if is_dst or mode == "olsr":
        return base
    if mode in ("add", "add-adaptive"):
        return base + a * (1.0 - c)
    if mode == "mult":
        return base * (1.0 + a * (1.0 - c))
    if mode == "threshold":
        return base + (a if c < args.thr else 0.0)
    raise ValueError(mode)


def base_cost(link, args):
    return 1.0 if args.base == "hop" else link[1]


def best_path(g, snap, s, d, mode, a, args):
    dist, prev, heap = {s: 0.0}, {}, [(0.0, s)]
    while heap:
        c, u = heapq.heappop(heap)
        if c > dist[u]:
            continue
        if u == d:
            break
        for v, lk in g[u].items():
            nc = c + edge_w(mode, base_cost(lk, args), snap[v], v == d, a, args)
            if nc < dist.get(v, INF):
                dist[v] = nc
                prev[v] = u
                heapq.heappush(heap, (nc, v))
    if d not in dist:
        return None, INF
    path = [d]
    while path[-1] != s:
        path.append(prev[path[-1]])
    return path[::-1], dist[d]


def path_cost(path, g, snap, mode, a, args):
    total = 0.0
    dst = path[-1]
    for x, y in zip(path, path[1:]):
        lk = g[x].get(y)
        if lk is None:
            return INF
        total += edge_w(mode, base_cost(lk, args), snap[y], y == dst, a, args)
    return total


# ----------------------------------------------------------------------------
# One configuration over one scenario
# ----------------------------------------------------------------------------
def simulate(sc, args, mode, alpha, H):
    n, flows = sc.n, sc.flows
    C = [1.0] * n
    snap = C[:]
    routes = [None] * len(flows)
    sent = deliv = withroute = lowpk = hops_sum = changes = 0
    delay_sum = 0.0
    last_sent = [1.0] * n   # value each node last advertised (for event-triggered updates)
    events = 0              # advertisements an event-triggered policy would send

    for t in range(sc.T):
        g, r = sc.graphs[t], sc.rel[t]

        if t % args.route_interval == 0:
            snap = C[:]  # what the network has "advertised"
            a = alpha
            if mode == "add-adaptive":
                frac_low = sum(1 for c in snap if c < LOW) / n
                a = args.alpha_lo + (args.alpha_hi - args.alpha_lo) * min(1.0, frac_low / args.frac_ref)
            for f, (s, d) in enumerate(flows):
                new, ncost = best_path(g, snap, s, d, mode, a, args)
                cur = routes[f]
                if cur is not None:
                    ccost = path_cost(cur, g, snap, mode, a, args)
                    if ccost < INF and (new is None or new == cur or ncost >= ccost * (1.0 - H) - 1e-12):
                        continue  # keep the working route (hysteresis)
                if new != cur:
                    if cur is not None and new is not None and t >= args.warmup:
                        changes += 1
                    routes[f] = new

        attempts, success = [0] * n, [0] * n
        counted = t >= args.warmup
        for f, (s, d) in enumerate(flows):
            if counted:
                sent += 1
            p = routes[f]
            if p is None:
                continue
            u = sc.u[t][f]
            low = any(r[x] < LOW for x in p[1:-1])
            ok, dl = True, 0.0
            for h in range(len(p) - 1):
                x, y = p[h], p[h + 1]
                lk = g[x].get(y)
                if lk is None or u[(2 * h) % 64] > lk[2]:
                    ok = False
                    break
                dl += 5.0 / lk[0] + 2.0  # expected tx attempts * 5 ms + 2 ms processing
                if y != d:
                    attempts[y] += 1
                    if u[(2 * h + 1) % 64] < r[y]:
                        success[y] += 1
                    else:
                        ok = False
                        break
            if counted:
                withroute += 1
                hops_sum += len(p) - 1
                lowpk += 1 if low else 0
                if ok:
                    deliv += 1
                    delay_sum += dl

        for i in range(n):
            if attempts[i]:
                C[i] = args.lam * C[i] + (1.0 - args.lam) * (success[i] / attempts[i])
            else:
                C[i] += args.recovery * (1.0 - C[i])
            if abs(C[i] - last_sent[i]) > args.delta:
                last_sent[i] = C[i]
                if t >= args.warmup:
                    events += 1

    minutes = max(1e-9, (sc.T - args.warmup) / 60.0)
    return {
        "pdr": deliv / sent if sent else 0.0,
        "hops": hops_sum / withroute if withroute else float("nan"),
        "delay_ms": delay_sum / deliv if deliv else float("nan"),
        "changes_pm": changes / (len(flows) * minutes) if flows else 0.0,
        "low_share": lowpk / withroute if withroute else 0.0,
        "events_ps": events / (n * max(1, sc.T - args.warmup)),
    }


# ----------------------------------------------------------------------------
# Experiment driver
# ----------------------------------------------------------------------------
def config_list(args):
    cfgs = [("olsr", 0.0, 0.0)]
    for h in args.hyst:
        if h > 0:
            cfgs.append(("olsr", 0.0, h))   # fair baseline: plain routing WITH the same hysteresis
    for mode in ("add", "mult", "threshold"):
        for a in args.alphas:
            if a == 0 and mode != "add":
                continue                      # alpha 0 is plain routing; keep it once, under "add"
            for h in args.hyst:
                cfgs.append((mode, a, h))
    for h in args.hyst:
        cfgs.append(("add-adaptive", float("nan"), h))
    return cfgs


def label(cfg):
    mode, a, h = cfg
    a_txt = "adapt" if a != a else f"{a:g}"
    if mode == "olsr":
        return "olsr" if h == 0 else f"olsr(H={h:g})"
    return f"{mode}(a={a_txt},H={h:g})"


def mean_ci(vals):
    v = [x for x in vals if x == x]
    if not v:
        return float("nan"), float("nan")
    if len(v) < 2:
        return v[0], 0.0
    return statistics.mean(v), 1.96 * statistics.stdev(v) / math.sqrt(len(v))


def overhead_model(args, events_ps):
    """Analytical control-overhead estimate in bytes per second for the whole network.
    All sizes and intervals are MODEL PARAMETERS: replace them with values measured in ns-3.
      baseline   HELLO from every node + TC floods from the fraction of nodes that originate them
      periodic   the confidence field is carried in every HELLO and TC
      event      the field is only sent when a node's confidence moved by more than --delta
                 (capped at the periodic cost)"""
    N = args.nodes
    flood = 1.0 + args.mpr_frac * N          # transmissions per TC flood
    base = N * args.hello_bytes / args.hello_int + N * args.tc_frac * args.tc_bytes * flood / args.tc_int
    b = args.conf_bytes
    periodic = N * b / args.hello_int + N * args.tc_frac * b * flood / args.tc_int
    event = min(periodic, N * events_ps * b * (1.0 + args.tc_frac * flood))
    return base, periodic, event


def alpha_sweep_summary(args, cfgs, agg, base):
    h0 = args.hyst[0]
    rows = sorted((c[1], agg[c]) for c in cfgs if c[0] == "add" and c[2] == h0)
    if len(rows) < 2:
        return
    gains = [100.0 * (m["pdr"][0] - base["pdr"][0]) / base["pdr"][0] for _, m in rows]
    top = max(gains)
    knee = next((a for (a, _), g in zip(rows, gains) if top > 0 and g >= 0.9 * top), None)
    print(f"\nAlpha sweep (additive, H={h0:g}): where do extra penalty returns diminish?")
    print(f"{'alpha':>6}{'PDR':>8}{'dPDR%':>8}{'step gain':>11}{'dDelay%':>9}{'dHops%':>8}")
    prev = 0.0
    for (a, m), g in zip(rows, gains):
        dd = 100.0 * (m["delay_ms"][0] - base["delay_ms"][0]) / base["delay_ms"][0]
        dh = 100.0 * (m["hops"][0] - base["hops"][0]) / base["hops"][0]
        mark = "  <- knee" if a == knee else ""
        print(f"{a:>6g}{m['pdr'][0]:>8.3f}{g:>8.1f}{g - prev:>+11.1f}{dd:>9.1f}{dh:>8.1f}{mark}")
        prev = g
    if knee is not None:
        print(f"Knee = smallest alpha reaching 90% of the best PDR gain in this sweep (alpha = {knee:g}). "
              "Larger alpha adds little reliability for more cost.")


def pareto_flags(points):
    """points: list of (pdr, delay). Returns set of indices not dominated."""
    keep = set()
    for i, (p, d) in enumerate(points):
        dominated = False
        for j, (p2, d2) in enumerate(points):
            if j != i and p2 >= p and d2 <= d and (p2 > p or d2 < d):
                dominated = True
                break
        if not dominated:
            keep.add(i)
    return keep


def sanity_check(args):
    sc = build_scenario(args, 999)
    a = simulate(sc, args, "olsr", 0.0, 0.0)
    b = simulate(sc, args, "add", 0.0, 0.0)
    for k in ("pdr", "hops", "delay_ms", "changes_pm"):
        assert abs(a[k] - b[k]) < 1e-9, (k, a[k], b[k])
    print("[sanity] add with alpha = 0 reproduces the olsr baseline exactly. OK\n")


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--nodes", type=int, default=50)
    ap.add_argument("--area", type=float, default=1000.0)
    ap.add_argument("--range", type=float, default=250.0)
    ap.add_argument("--flows", type=int, default=10)
    ap.add_argument("--time", type=int, default=300)
    ap.add_argument("--warmup", type=int, default=30)
    ap.add_argument("--speed", type=float, default=5.0, help="max speed m/s (0 = static)")
    ap.add_argument("--fragile", type=float, default=0.25, help="fraction of fragile nodes")
    ap.add_argument("--volatility", type=float, default=1.0, help="scales how fast reliability changes")
    ap.add_argument("--trials", type=int, default=20)
    ap.add_argument("--base", choices=["hop", "etx"], default="hop")
    ap.add_argument("--lam", type=float, default=0.8, help="EMA weight on old confidence")
    ap.add_argument("--recovery", type=float, default=0.02, help="drift toward 1 with no observations")
    ap.add_argument("--route-interval", dest="route_interval", type=int, default=5)
    ap.add_argument("--alphas", type=float, nargs="+", default=[0, 1, 2, 4, 8, 16])
    ap.add_argument("--hyst", type=float, nargs="+", default=[0.0, 0.1])
    ap.add_argument("--thr", type=float, default=0.7, help="threshold-mode cutoff")
    ap.add_argument("--alpha-lo", dest="alpha_lo", type=float, default=1.0)
    ap.add_argument("--alpha-hi", dest="alpha_hi", type=float, default=8.0)
    ap.add_argument("--frac-ref", dest="frac_ref", type=float, default=0.25,
                    help="known-low fraction at which adaptive alpha reaches alpha-hi")
    ap.add_argument("--delta", type=float, default=0.05, help="event-trigger: advertise when confidence moves by more than this")
    ap.add_argument("--conf-bytes", dest="conf_bytes", type=float, default=2.0, help="bytes added per HELLO/TC (0 for the reserved-bits variant)")
    ap.add_argument("--hello-bytes", dest="hello_bytes", type=float, default=60.0)
    ap.add_argument("--tc-bytes", dest="tc_bytes", type=float, default=90.0)
    ap.add_argument("--hello-int", dest="hello_int", type=float, default=2.0)
    ap.add_argument("--tc-int", dest="tc_int", type=float, default=5.0)
    ap.add_argument("--tc-frac", dest="tc_frac", type=float, default=0.5, help="share of nodes that originate TC")
    ap.add_argument("--mpr-frac", dest="mpr_frac", type=float, default=0.3, help="share of nodes that retransmit a TC flood")
    ap.add_argument("--max-ovh-inc", dest="max_ovh_inc", type=float, default=10.0, help="%%")
    ap.add_argument("--min-gain", dest="min_gain", type=float, default=5.0, help="min relative PDR gain, %%")
    ap.add_argument("--max-delay-inc", dest="max_delay_inc", type=float, default=10.0, help="%%")
    ap.add_argument("--max-hop-inc", dest="max_hop_inc", type=float, default=15.0, help="%%")
    ap.add_argument("--csv", type=str, default=None, help="write raw per-seed results here")
    ap.add_argument("--plot", type=str, default=None, help="directory for plots")
    return ap


def main():
    args = build_parser().parse_args()

    sanity_check(args)

    cfgs = config_list(args)
    raw = {c: [] for c in cfgs}
    for seed in range(1, args.trials + 1):
        sc = build_scenario(args, seed)
        if not sc.flows:
            continue
        for c in cfgs:
            res = simulate(sc, args, *c)
            res["seed"] = seed
            raw[c].append(res)

    agg = {}
    for c in cfgs:
        agg[c] = {k: mean_ci([r[k] for r in raw[c]])
                  for k in ("pdr", "hops", "delay_ms", "changes_pm", "low_share", "events_ps")}

    base = agg[cfgs[0]]
    pareto = pareto_flags([(agg[c]["pdr"][0], agg[c]["delay_ms"][0]) for c in cfgs])

    print(f"nodes={args.nodes} fragile={args.fragile} speed={args.speed} base={args.base} "
          f"trials={args.trials} time={args.time}s warmup={args.warmup}s")
    ob, op, _ = overhead_model(args, 0.0)
    ovh_periodic_pct = 100.0 * op / ob if ob else 0.0
    print(f"overhead model: baseline control {ob:.0f} B/s; confidence field of {args.conf_bytes} B per message "
          f"adds {ovh_periodic_pct:.1f}% if periodic (model parameters, replace with ns-3 measurements)")
    print(f"acceptable = PDR gain >= {args.min_gain}% (relative), delay inc <= {args.max_delay_inc}%, "
          f"hop inc <= {args.max_hop_inc}%, periodic overhead inc <= {args.max_ovh_inc}%\n")
    hdr = f"{'config':<28}{'PDR':>7}{'+-':>7}{'dPDR%':>7}{'hops':>6}{'dHop%':>7}{'delay':>8}{'dDel%':>7}{'chg/min':>8}{'low%':>6}{'ovh_ev%':>8}  flags"
    print(hdr)
    print("-" * len(hdr))
    order = sorted(range(len(cfgs)), key=lambda i: -agg[cfgs[i]]["pdr"][0])
    n_ok = 0
    for i in order:
        c = cfgs[i]
        m = agg[c]
        d_pdr = 100.0 * (m["pdr"][0] - base["pdr"][0]) / base["pdr"][0] if base["pdr"][0] else float("nan")
        d_hop = 100.0 * (m["hops"][0] - base["hops"][0]) / base["hops"][0]
        d_del = 100.0 * (m["delay_ms"][0] - base["delay_ms"][0]) / base["delay_ms"][0]
        _, _, ev = overhead_model(args, m["events_ps"][0])
        ovh_ev = 100.0 * ev / ob if ob else 0.0
        ok = (c[0] != "olsr" and d_pdr >= args.min_gain and d_del <= args.max_delay_inc
              and d_hop <= args.max_hop_inc and ovh_periodic_pct <= args.max_ovh_inc)
        n_ok += ok
        flags = ("A" if ok else "-") + ("P" if i in pareto else "-")
        print(f"{label(c):<28}{m['pdr'][0]:>7.3f}{m['pdr'][1]:>7.3f}{d_pdr:>7.1f}{m['hops'][0]:>6.2f}"
              f"{d_hop:>7.1f}{m['delay_ms'][0]:>8.1f}{d_del:>7.1f}{m['changes_pm'][0]:>8.2f}"
              f"{100 * m['low_share'][0]:>6.1f}{ovh_ev:>8.2f}  {flags}")
    print(f"\n{n_ok} of {sum(1 for c in cfgs if c[0] != 'olsr')} confidence-aware configurations meet the acceptability criteria.")
    print("Note: 'olsr(H=...)' rows are the FAIR baseline (plain routing with the same hysteresis). "
          "Judge hysteresis against them, not against plain olsr.")
    alpha_sweep_summary(args, cfgs, agg, base)
    print("Delay is a proxy (expected MAC attempts x 5 ms + 2 ms per hop, delivered packets only). "
          "Overhead is an analytical estimate (see --conf-bytes, --hello-bytes, ...), not a measurement.")

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["mode", "alpha", "hyst", "seed", "pdr", "hops", "delay_ms", "changes_pm", "low_share"])
            for c in cfgs:
                for r in raw[c]:
                    w.writerow([c[0], c[1], c[2], r["seed"], r["pdr"], r["hops"], r["delay_ms"],
                                r["changes_pm"], r["low_share"]])
        print(f"saved {args.csv}")

    if args.plot:
        make_plots(args, cfgs, agg, pareto)


def make_plots(args, cfgs, agg, pareto):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping plots")
        return
    os.makedirs(args.plot, exist_ok=True)

    # 1. Reliability vs routing cost (Pareto view)
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    colors = {"olsr": "black", "add": "tab:blue", "mult": "tab:orange",
              "threshold": "tab:green", "add-adaptive": "tab:red"}
    for i, c in enumerate(cfgs):
        m = agg[c]
        ax.scatter(m["delay_ms"][0], m["pdr"][0], color=colors[c[0]], s=60 if i in pareto else 25,
                   marker="*" if i in pareto else "o", label=c[0] if c[0] not in ax.get_legend_handles_labels()[1] else None)
    front = sorted((agg[cfgs[i]]["delay_ms"][0], agg[cfgs[i]]["pdr"][0]) for i in pareto)
    ax.plot([p[0] for p in front], [p[1] for p in front], "k--", lw=0.8)
    ax.set_xlabel("Mean delay proxy (ms)")
    ax.set_ylabel("Packet delivery ratio")
    ax.set_title("Reliability vs routing cost (stars = Pareto frontier)")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(args.plot, "pareto_pdr_vs_delay.png"), dpi=200)
    plt.close(fig)

    # 2. Alpha sweeps (H = first hysteresis value)
    h0 = args.hyst[0]
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    for mode in ("add", "mult", "threshold"):
        pts = [(c[1], agg[c]) for c in cfgs if c[0] == mode and c[2] == h0]
        pts.sort()
        for ax, key, yl in zip(axes, ("pdr", "hops", "delay_ms"), ("PDR", "Average hops", "Delay proxy (ms)")):
            ax.errorbar([p[0] for p in pts], [p[1][key][0] for p in pts], yerr=[p[1][key][1] for p in pts],
                        marker="o", capsize=3, label=mode, color=colors[mode])
            ax.set_xlabel("alpha")
            ax.set_ylabel(yl)
            ax.set_xscale("symlog", base=2, linthresh=1.0)
            ax.grid(alpha=0.3)
    for ax, key in zip(axes, ("pdr", "hops", "delay_ms")):
        ax.axhline(agg[cfgs[0]][key][0], color="black", ls=":", label="olsr")
    axes[0].legend()
    fig.tight_layout()
    fig.savefig(os.path.join(args.plot, "alpha_sweep.png"), dpi=200)
    plt.close(fig)

    # 3. Route changes vs hysteresis (additive mode, largest alpha in the sweep)
    amax = max(args.alphas)
    pts = sorted((c[2], agg[c]["changes_pm"]) for c in cfgs if c[0] == "add" and c[1] == amax)
    if len(pts) > 1:
        fig, ax = plt.subplots(figsize=(5, 3.8))
        ax.errorbar([p[0] for p in pts], [p[1][0] for p in pts], yerr=[p[1][1] for p in pts], marker="o", capsize=3)
        ax.axhline(agg[cfgs[0]]["changes_pm"][0], color="black", ls=":", label="olsr")
        ax.set_xlabel("Hysteresis H")
        ax.set_ylabel("Route changes per flow per minute")
        ax.set_title(f"Route stability (add, alpha={amax:g})")
        ax.grid(alpha=0.3)
        ax.legend()
        fig.tight_layout()
        fig.savefig(os.path.join(args.plot, "hysteresis_route_changes.png"), dpi=200)
        plt.close(fig)
    print(f"plots saved in {args.plot}/")


if __name__ == "__main__":
    main()
