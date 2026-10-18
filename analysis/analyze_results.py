#!/usr/bin/env python3
"""
analyze_results.py
==================
Turns the CSV that your ns-3 scenario writes into summary tables and the
plots listed in the guide.

Expected CSV columns (one row per simulation run):
    proto, nNodes, speed, fragile, alpha, run,
    pdr, meanDelay, ctrlBytes, ctrlPkts, routeChanges,
    lowRelayShare, usefulDelivery

  proto   label of the series, e.g. olsr-hop, uar-mult, uar-add, uar-threshold
  fragile fraction of low-confidence nodes (0 to 1)

Usage
    python3 analyze_results.py results.csv            # real data
    python3 analyze_results.py --demo                 # fake data, to test the script

Output goes to ./figures/ (PNG) and ./summary_*.csv
"""

import argparse
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

METRICS = ["pdr", "meanDelay", "ctrlBytes", "routeChanges", "lowRelayShare", "usefulDelivery"]


def make_demo_data(path):
    """Synthetic data with the SHAPE you hope to see. Only for testing the script.
    Do NOT put these numbers in a paper."""
    rng = np.random.default_rng(0)
    rows = []
    for proto, gain in [("olsr-hop", 0.0), ("uar-mult", 0.5), ("uar-add", 0.45), ("uar-threshold", 0.7)]:
        for n in (20, 50, 100):
            for f in (0.0, 0.1, 0.25, 0.5):
                for run in range(1, 21):
                    low = f * (1 - gain) * 1.4 + rng.normal(0, 0.02)
                    rows.append(
                        dict(
                            proto=proto, nNodes=n, speed=5, fragile=f, alpha=4, run=run,
                            pdr=max(0, 0.95 - 0.1 * f * (gain > 0.6) - 0.001 * n + rng.normal(0, 0.01)),
                            meanDelay=0.05 + 0.03 * gain * f + rng.normal(0, 0.003),
                            ctrlBytes=n * 900 * (1.0 if proto == "olsr-hop" else 1.02) + rng.normal(0, 200),
                            ctrlPkts=n * 40,
                            routeChanges=3 + 4 * gain + rng.normal(0, 0.5),
                            lowRelayShare=min(1, max(0, low)),
                            usefulDelivery=max(0, 1 - 0.7 * low + rng.normal(0, 0.02)),
                        )
                    )
    pd.DataFrame(rows).to_csv(path, index=False)
    print(f"wrote demo data to {path}")


def ci95(series):
    n = series.count()
    return 1.96 * series.std(ddof=1) / np.sqrt(n) if n > 1 else 0.0


def summarize(df, by, metric):
    g = df.groupby(by)[metric]
    out = g.agg(["mean", "std", "count"])
    out["ci95"] = g.apply(ci95)
    return out.reset_index()


def line_plot(df, x, metric, ylabel, fname, filt=None, title=None):
    d = df if filt is None else df.query(filt)
    if d.empty:
        print(f"skip {fname}: no rows for filter {filt}")
        return
    s = summarize(d, ["proto", x], metric)
    fig, ax = plt.subplots(figsize=(6, 4))
    for proto, grp in s.groupby("proto"):
        grp = grp.sort_values(x)
        ax.errorbar(grp[x], grp["mean"], yerr=grp["ci95"], marker="o", capsize=3, label=proto)
    ax.set_xlabel(x)
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join("figures", fname), dpi=200)
    plt.close(fig)
    print(f"saved figures/{fname}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?", help="results CSV from ns-3")
    ap.add_argument("--demo", action="store_true", help="generate and analyze fake demo data")
    ap.add_argument("--nodes", type=int, default=50, help="network size used for the fragile-fraction plots")
    args = ap.parse_args()

    if args.demo:
        args.csv = "demo_results.csv"
        make_demo_data(args.csv)
    if not args.csv:
        ap.error("give a CSV file or use --demo")

    df = pd.read_csv(args.csv)
    missing = [c for c in ["proto", "nNodes", "fragile", "run"] + METRICS if c not in df.columns]
    if missing:
        sys.exit(f"CSV is missing columns: {missing}")

    os.makedirs("figures", exist_ok=True)

    # ---- summary tables ----
    for metric in METRICS:
        summarize(df, ["proto", "nNodes", "fragile"], metric).to_csv(f"summary_{metric}.csv", index=False)
    print("saved summary_<metric>.csv for each metric")

    n = args.nodes
    base = f"nNodes == {n}"

    # ---- headline figures ----
    line_plot(df, "fragile", "usefulDelivery", "Useful delivery", "01_useful_vs_fragile.png", base,
              f"Useful delivery vs low-confidence fraction (N={n})")
    line_plot(df, "fragile", "lowRelayShare", "Share of flows via low-confidence relay", "02_lowrelay_vs_fragile.png", base)
    line_plot(df, "fragile", "pdr", "Packet delivery ratio", "04a_pdr_vs_fragile.png", base)
    line_plot(df, "fragile", "meanDelay", "Mean end-to-end delay (s)", "04b_delay_vs_fragile.png", base)
    line_plot(df, "fragile", "routeChanges", "Route changes per minute", "06_routechanges_vs_fragile.png", base)

    # ---- overhead vs network size ----
    line_plot(df, "nNodes", "ctrlBytes", "Control bytes", "03_overhead_vs_size.png")

    # ---- sensitivity to alpha (only if more than one alpha was run) ----
    if "alpha" in df.columns and df["alpha"].nunique() > 1:
        line_plot(df, "alpha", "usefulDelivery", "Useful delivery", "05_useful_vs_alpha.png",
                  f"{base} and fragile == 0.25")

    # ---- paired comparison against a baseline, same seeds ----
    if "olsr-hop" in df["proto"].unique():
        key = ["nNodes", "fragile", "alpha", "speed", "run"]
        key = [k for k in key if k in df.columns]
        piv = df.pivot_table(index=key, columns="proto", values="usefulDelivery")
        base_col = "olsr-hop"
        print("\nPaired improvement in useful delivery over olsr-hop (mean difference, 95% CI):")
        for proto in piv.columns:
            if proto == base_col:
                continue
            diff = (piv[proto] - piv[base_col]).dropna()
            if len(diff) > 1:
                print(f"  {proto:<16} {diff.mean():+.4f}  +- {1.96 * diff.std(ddof=1) / np.sqrt(len(diff)):.4f}  (n={len(diff)})")


if __name__ == "__main__":
    main()
