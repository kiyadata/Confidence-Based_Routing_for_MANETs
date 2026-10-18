#!/usr/bin/env python3
"""
uar_boundary.py : "When is confidence-aware routing worth it?"
===============================================================
Answers the secondary research question with a map instead of one number:

    Under what network conditions does dynamically confidence-aware OLSR give
    a net reliability benefit, and when is plain OLSR enough?

For every cell of a grid (node speed x fraction of unreliable nodes) it runs,
on identical scenarios and random draws:
    olsr      plain routing
    olsr_h    plain routing WITH hysteresis H   (fair baseline for stability)
    conf      additive confidence routing, hysteresis 0
    conf_h    additive confidence routing, hysteresis H

and labels the cell with the FIRST rule that applies (rules are fixed here, in
advance, and can be changed only with a stated reason):

    OLSR sufficient       PDR gain of conf_h over olsr is below --min-gain %,
                          or its paired 95% confidence interval includes zero
    too costly            gain is real but delay or hop increase exceeds the limit
    needs hysteresis      gain is real and affordable, but conf (no hysteresis)
                          changes routes more than the allowance, while conf_h does not
    unstable              conf_h still changes routes more than the allowance
    (allowance = (1 + --tol) x olsr route changes + --abs-tol changes per flow per minute.
     The absolute part is needed because a static network gives plain routing ZERO route
     changes, and a purely relative rule would then call any change unstable. It was added
     after a first run exposed that flaw, so state it as a design choice in the paper.)
    beneficial            none of the above: real, affordable, stable gain

Run
    python3 uar_boundary.py                      # default grid, 12 seeds per cell
    python3 uar_boundary.py --trials 20 --alpha 4 --H 0.1 --base etx --plot figs

Output: a table, boundary.csv, and (with --plot DIR) a colour map.
"""

import argparse
import csv
import math
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import uar_dynamic as ud  # noqa: E402

CATEGORIES = ["OLSR sufficient", "beneficial", "needs hysteresis", "too costly", "unstable"]
COLORS = {"OLSR sufficient": "#d9d9d9", "beneficial": "#8fd19e", "needs hysteresis": "#ffd27f",
          "too costly": "#f4a6a6", "unstable": "#c9a0dc"}


def paired(a, b):
    """mean and 95% CI of b - a over seeds"""
    d = [y - x for x, y in zip(a, b)]
    if len(d) < 2:
        return (d[0] if d else float("nan")), 0.0
    return statistics.mean(d), 1.96 * statistics.stdev(d) / math.sqrt(len(d))


def run_cell(base_args, speed, frac, trials, alpha, H):
    a = argparse.Namespace(**vars(base_args))
    a.speed, a.fragile = speed, frac
    keys = ("olsr", "olsr_h", "conf", "conf_h")
    out = {k: [] for k in keys}
    for seed in range(1, trials + 1):
        sc = ud.build_scenario(a, seed)
        if not sc.flows:
            continue
        out["olsr"].append(ud.simulate(sc, a, "olsr", 0.0, 0.0))
        out["olsr_h"].append(ud.simulate(sc, a, "olsr", 0.0, H))
        out["conf"].append(ud.simulate(sc, a, "add", alpha, 0.0))
        out["conf_h"].append(ud.simulate(sc, a, "add", alpha, H))
    return out


def mean_of(runs, key):
    vals = [r[key] for r in runs if r[key] == r[key]]
    return statistics.mean(vals) if vals else float("nan")


def classify(res, args):
    pdr_o = [r["pdr"] for r in res["olsr"]]
    pdr_c = [r["pdr"] for r in res["conf_h"]]
    diff, ci = paired(pdr_o, pdr_c)
    base = statistics.mean(pdr_o) if pdr_o else float("nan")
    gain = 100.0 * diff / base if base else float("nan")
    d_delay = 100.0 * (mean_of(res["conf_h"], "delay_ms") - mean_of(res["olsr"], "delay_ms")) / mean_of(res["olsr"], "delay_ms")
    d_hops = 100.0 * (mean_of(res["conf_h"], "hops") - mean_of(res["olsr"], "hops")) / mean_of(res["olsr"], "hops")
    chg_o = mean_of(res["olsr"], "changes_pm")
    chg_c = mean_of(res["conf"], "changes_pm")
    chg_ch = mean_of(res["conf_h"], "changes_pm")
    info = {"gain": gain, "ci_lo": diff - ci, "d_delay": d_delay, "d_hops": d_hops,
            "chg_olsr": chg_o, "chg_conf": chg_c, "chg_conf_h": chg_ch,
            "chg_olsr_h": mean_of(res["olsr_h"], "changes_pm"),
            "pdr_olsr": base, "pdr_conf_h": statistics.mean(pdr_c) if pdr_c else float("nan")}
    if not (gain >= args.min_gain and diff - ci > 0):
        return "OLSR sufficient", info
    if d_delay > args.max_delay_inc or d_hops > args.max_hop_inc:
        return "too costly", info
    allowance = (1 + args.tol) * chg_o + args.abs_tol
    unstable_plain = chg_c > allowance
    unstable_h = chg_ch > allowance
    if unstable_h:
        return "unstable", info
    if unstable_plain:
        return "needs hysteresis", info
    return "beneficial", info


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter,
                                 allow_abbrev=False)
    ap.add_argument("--speeds", type=float, nargs="+", default=[0.0, 5.0, 15.0])
    ap.add_argument("--fractions", type=float, nargs="+", default=[0.0, 0.1, 0.25, 0.5])
    ap.add_argument("--trials", type=int, default=12)
    ap.add_argument("--alpha", type=float, default=4.0)
    ap.add_argument("--H", type=float, default=0.1)
    ap.add_argument("--tol", type=float, default=0.25, help="allowed route-change increase over olsr")
    ap.add_argument("--abs-tol", dest="abs_tol", type=float, default=1.0,
                    help="extra allowed route changes per flow per minute")
    ap.add_argument("--csv", default="boundary.csv")
    ap.add_argument("--plot", default=None)
    own, rest = ap.parse_known_args()

    # reuse every default (and flag) of the main prototype for the remaining settings
    base = ud.build_parser().parse_args(rest)
    for k in ("min_gain", "max_delay_inc", "max_hop_inc"):
        setattr(own, k, getattr(base, k))

    grid, rows = {}, []
    print(f"alpha={own.alpha:g}  H={own.H:g}  base={base.base}  nodes={base.nodes}  trials={own.trials}")
    print(f"rules: gain >= {own.min_gain}% and paired CI above 0; delay inc <= {own.max_delay_inc}%; "
          f"hop inc <= {own.max_hop_inc}%; route-change allowance {own.tol:.0%} + {own.abs_tol:g}/min\n")
    for frac in own.fractions:
        for speed in own.speeds:
            res = run_cell(base, speed, frac, own.trials, own.alpha, own.H)
            label, info = classify(res, own)
            grid[(frac, speed)] = label
            rows.append({"fragile": frac, "speed": speed, "label": label, **info})
            print(f"fragile={frac:<5g} speed={speed:<5g} -> {label:<17} "
                  f"gain={info['gain']:>6.1f}%  dDelay={info['d_delay']:>5.1f}%  dHops={info['d_hops']:>5.1f}%  "
                  f"chg/min olsr={info['chg_olsr']:.2f} conf={info['chg_conf']:.2f} conf_h={info['chg_conf_h']:.2f}")

    print("\nDecision map (rows: fraction of unreliable nodes, columns: max node speed m/s)")
    print(f"{'':>10}" + "".join(f"{s:>20g}" for s in own.speeds))
    for frac in own.fractions:
        print(f"{frac:>10g}" + "".join(f"{grid[(frac, s)]:>20}" for s in own.speeds))

    with open(own.csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nsaved {own.csv}")

    if own.plot:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from matplotlib.colors import ListedColormap
            from matplotlib.patches import Patch
        except ImportError:
            print("matplotlib not installed; skipping plot")
            return
        os.makedirs(own.plot, exist_ok=True)
        idx = {c: i for i, c in enumerate(CATEGORIES)}
        mat = [[idx[grid[(f, s)]] for s in own.speeds] for f in own.fractions]
        fig, ax = plt.subplots(figsize=(6.5, 4.2))
        ax.imshow(mat, cmap=ListedColormap([COLORS[c] for c in CATEGORIES]), vmin=0, vmax=len(CATEGORIES) - 1,
                  origin="lower", aspect="auto")
        for i, f in enumerate(own.fractions):
            for j, s in enumerate(own.speeds):
                r = next(x for x in rows if x["fragile"] == f and x["speed"] == s)
                ax.text(j, i, f"{r['gain']:+.0f}%", ha="center", va="center", fontsize=9)
        ax.set_xticks(range(len(own.speeds)))
        ax.set_xticklabels([f"{s:g}" for s in own.speeds])
        ax.set_yticks(range(len(own.fractions)))
        ax.set_yticklabels([f"{f:.0%}" for f in own.fractions])
        ax.set_xlabel("Max node speed (m/s)")
        ax.set_ylabel("Fraction of unreliable nodes")
        ax.set_title(f"When does confidence-aware routing pay off? (alpha={own.alpha:g}, H={own.H:g})")
        ax.legend(handles=[Patch(color=COLORS[c], label=c) for c in CATEGORIES],
                  loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=8)
        fig.tight_layout()
        path = os.path.join(own.plot, "decision_map.png")
        fig.savefig(path, dpi=200)
        plt.close(fig)
        print(f"saved {path}  (numbers in cells = PDR gain over plain routing)")


if __name__ == "__main__":
    main()
