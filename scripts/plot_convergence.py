"""Plot exploitability vs iterations for CFR and CFR+ on Kuhn and Leduc.

Saves figures/kuhn_convergence.png and figures/leduc_convergence.png, and
prints the measured "CFR+ reaches the same exploitability in N-fewer iterations"
speedup for each game.
"""

import _bootstrap  # noqa: F401

import argparse
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from cfr_poker.experiments import compare_cfr_variants, speedup_at
from cfr_poker.games import KuhnPoker, LeducPoker

FIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "figures")


def plot_game(name, game, max_iters, target=None):
    tree, curves = compare_cfr_variants(game, max_iters)
    fig, ax = plt.subplots(figsize=(7, 5))
    styles = {"vanilla": dict(color="#c1121f", marker="o"),
              "cfr+": dict(color="#023e8a", marker="s")}
    labels = {"vanilla": "CFR (average strategy)", "cfr+": "CFR+ (current strategy)"}
    for key, (xs, ys) in curves.items():
        ax.loglog(xs, ys, label=labels[key], markersize=3, linewidth=1.5, **styles[key])

    # Auto-target: the exploitability vanilla reaches by max_iters. Both curves
    # reach it, so the speedup answers "how many fewer iterations does CFR+ need
    # to match CFR's best result?".
    if target is None:
        target = curves["vanilla"][1][-1] * 1.05
    sp = speedup_at(curves["vanilla"], curves["cfr+"], target)
    if sp is not None:
        slow, fast, ratio = sp
        ax.axhline(target, color="gray", ls="--", lw=0.8)
        ax.annotate(f"{ratio:.1f}x fewer iters to reach {target:g}",
                    xy=(fast, target), xytext=(fast, target * 4),
                    fontsize=9, color="black")
        print(f"{name}: CFR+ reaches {target:g} at ~{fast:.0f} iters; "
              f"CFR needs ~{slow:.0f} -> {ratio:.1f}x speedup")
    else:
        print(f"{name}: target {target:g} not reached by both within {max_iters} iters")

    ax.set_xlabel("iterations")
    ax.set_ylabel("exploitability (chips / game)")
    ax.set_title(f"{name}: CFR vs CFR+ convergence")
    ax.grid(True, which="both", ls=":", alpha=0.4)
    ax.legend()
    out = os.path.join(FIG_DIR, f"{game.name}_convergence.png")
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    print(f"  saved {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kuhn-iters", type=int, default=20000)
    ap.add_argument("--leduc-iters", type=int, default=8000)
    args = ap.parse_args()
    os.makedirs(FIG_DIR, exist_ok=True)
    plot_game("Kuhn poker", KuhnPoker(), args.kuhn_iters)
    plot_game("Leduc Hold'em", LeducPoker(), args.leduc_iters)


if __name__ == "__main__":
    main()
