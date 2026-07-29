"""Helpers for producing convergence curves and the CFR-vs-CFR+ comparison."""

from __future__ import annotations

import numpy as np

from .best_response import tree_exploitability
from .cfr import CFRSolver, cfr_plus, vanilla_cfr
from .tree import GameTree


def log_checkpoints(max_iters: int, per_decade: int = 12) -> list:
    """Log-spaced iteration checkpoints in [1, max_iters]."""
    lo, hi = 0.0, np.log10(max_iters)
    pts = np.unique(np.round(np.logspace(lo, hi, int(per_decade * hi) + 1)).astype(int))
    return [int(p) for p in pts if p >= 1]


def convergence_curve(tree: GameTree, solver: CFRSolver, checkpoints, report="solution"):
    """Run ``solver`` on ``tree``, returning (iterations, exploitability) lists.

    ``report`` selects which strategy's exploitability to measure:
    ``"solution"`` (average for CFR, current for CFR+), ``"average"``, or
    ``"current"``.
    """
    getter = {
        "solution": solver.solution_tree,
        "average": solver.average_strategy_tree,
        "current": solver.current_strategy_tree,
    }[report]
    xs, ys = [], []
    for m in checkpoints:
        if m > solver.iterations:
            solver.iterate(m - solver.iterations)
        xs.append(solver.iterations)
        ys.append(tree_exploitability(tree, getter()))
    return xs, ys


def compare_cfr_variants(game, max_iters: int):
    """Return {'vanilla': (xs, ys), 'cfr+': (xs, ys)} of exploitability curves."""
    tree = GameTree(game)
    checkpoints = log_checkpoints(max_iters)
    return tree, {
        "vanilla": convergence_curve(tree, vanilla_cfr(game, tree=tree), checkpoints),
        "cfr+": convergence_curve(tree, cfr_plus(game, tree=tree), checkpoints),
    }


def speedup_at(curve_slow, curve_fast, target: float):
    """Iterations each curve needs to first reach ``target`` exploitability.

    Returns (slow_iters, fast_iters, ratio) using linear interpolation in
    log-log space, or ``None`` if either curve never reaches the target.
    """
    def first_reach(xs, ys):
        for i in range(1, len(ys)):
            if ys[i] <= target:
                x0, x1 = np.log(xs[i - 1]), np.log(xs[i])
                y0, y1 = np.log(ys[i - 1]), np.log(ys[i])
                if y1 == y0:
                    return xs[i]
                frac = (np.log(target) - y0) / (y1 - y0)
                return float(np.exp(x0 + frac * (x1 - x0)))
        return None

    slow = first_reach(*curve_slow)
    fast = first_reach(*curve_fast)
    if slow is None or fast is None:
        return None
    return slow, fast, slow / fast
