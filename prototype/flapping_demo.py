#!/usr/bin/env python3
"""
flapping_demo.py : why hysteresis is needed (a 10-second picture for your teacher)
================================================================================
Two routes to the same destination. Both have the same number of hops, so the
only thing that separates them is the confidence of their relay node.

  Route A relay confidence ~ 0.70 and drifting
  Route B relay confidence ~ 0.69 and drifting

The two values keep crossing each other by tiny amounts. Without hysteresis the
router switches every time they cross. With hysteresis H it only switches when
the other route is cheaper by more than a factor H.

    cost(route) = base + alpha * (1 - confidence)
    switch only if  cost_new < cost_current * (1 - H)

Run
    python3 flapping_demo.py                  # prints switch counts
    python3 flapping_demo.py --plot demo.png  # also saves the figure
"""

import argparse
import math
import random


def simulate(H, alpha, steps, seed):
    rng = random.Random(seed)
    base = 3.0  # same hop cost for both routes
    cur, switches, chosen, ca_hist, cb_hist = "A", 0, [], [], []
    for t in range(steps):
        # slow drifts plus small noise, so the two curves keep crossing
        ca = 0.70 + 0.04 * math.sin(t / 7.0) + rng.gauss(0, 0.012)
        cb = 0.69 + 0.04 * math.sin(t / 7.0 + 1.3) + rng.gauss(0, 0.012)
        cost = {"A": base + alpha * (1 - ca), "B": base + alpha * (1 - cb)}
        best = min(cost, key=cost.get)
        if best != cur and cost[best] < cost[cur] * (1.0 - H):
            cur = best
            switches += 1
        chosen.append(cur)
        ca_hist.append(ca)
        cb_hist.append(cb)
    return switches, chosen, ca_hist, cb_hist


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--alpha", type=float, default=4.0)
    ap.add_argument("--steps", type=int, default=120)
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--plot", type=str, default=None)
    args = ap.parse_args()

    print(f"{args.steps} seconds, alpha = {args.alpha:g}, two routes with nearly equal confidence\n")
    print(f"{'hysteresis H':>14}{'route switches':>18}")
    results = {}
    for H in (0.0, 0.02, 0.05, 0.10, 0.15):
        sw, chosen, ca, cb = simulate(H, args.alpha, args.steps, args.seed)
        results[H] = (sw, chosen)
        print(f"{H:>14.2f}{sw:>18d}")
    print("\nWithout hysteresis the route flips whenever the confidences cross. "
          "A small margin removes almost all of the useless switches.")

    if args.plot:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        _, _, ca, cb = simulate(0.0, args.alpha, args.steps, args.seed)
        fig, axes = plt.subplots(3, 1, figsize=(7, 6), sharex=True,
                                 gridspec_kw={"height_ratios": [2, 1, 1]})
        axes[0].plot(ca, label="Route A relay confidence")
        axes[0].plot(cb, label="Route B relay confidence")
        axes[0].set_ylabel("Confidence")
        axes[0].legend(loc="upper right", fontsize=8)
        axes[0].set_title("Two nearly equal routes: confidence keeps crossing")
        for ax, H in zip(axes[1:], (0.0, 0.10)):
            sw, chosen = results[H]
            ax.step(range(len(chosen)), [1 if c == "A" else 0 for c in chosen], where="post")
            ax.set_yticks([0, 1])
            ax.set_yticklabels(["B", "A"])
            ax.set_ylabel("Route used")
            ax.set_title(f"Hysteresis H = {H:g}: {sw} route switches", fontsize=9)
        axes[-1].set_xlabel("Time (s)")
        fig.tight_layout()
        fig.savefig(args.plot, dpi=200)
        print(f"saved {args.plot}")


if __name__ == "__main__":
    main()
