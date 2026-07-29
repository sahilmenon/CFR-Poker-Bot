"""Solve both games and export strategies + validation numbers for the web demo.

Writes web/data/{kuhn,leduc}.json (per-info-set strategies keyed exactly as the
Python solver keys them, so the client-side engine can look them up) and copies
the convergence figures into web/assets/.
"""

import _bootstrap  # noqa: F401

import argparse
import json
import os
import shutil

from cfr_poker.analytic import KUHN_GAME_VALUE, kuhn_alpha_consistency
from cfr_poker.best_response import tree_exploitability
from cfr_poker.cfr import cfr_plus
from cfr_poker.evaluate import expected_value, strategy_from_table
from cfr_poker.games import KuhnPoker, LeducPoker
from cfr_poker.games.kuhn import PASS, BET
from cfr_poker.games.leduc import FOLD, CALL, RAISE
from cfr_poker.tree import GameTree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")

KUHN_ACTIONS = {PASS: "pass", BET: "bet"}
LEDUC_ACTIONS = {FOLD: "fold", CALL: "call", RAISE: "raise"}


def _strategy_dict(tree, strat_tree, action_names):
    """{info_set_key: {action_name: prob}} for legal actions only."""
    out = {}
    for iset, key in enumerate(tree.iset_key):
        probs = strat_tree[iset]
        actions = tree.iset_actions[iset]
        out[key] = {action_names[a]: round(float(p), 6) for a, p in zip(actions, probs)}
    return out


def export_kuhn(iters):
    game = KuhnPoker()
    tree = GameTree(game)
    solver = cfr_plus(game, tree=tree)
    solver.iterate(iters)
    table = solver.solution()
    sigma = strategy_from_table(game, table)
    alpha = kuhn_alpha_consistency(table)
    return {
        "game": "kuhn",
        "meta": {
            "iters": iters,
            "infosets": tree.num_infosets,
            "value": round(expected_value(game, sigma, sigma), 6),
            "value_truth": round(KUHN_GAME_VALUE, 6),
            "exploitability": float(f"{tree_exploitability(tree, solver.solution_tree()):.3e}"),
            "jack_bet": round(alpha["jack_bet"], 4),
            "queen_bet": round(alpha["queen_bet"], 4),
            "king_bet": round(alpha["king_bet"], 4),
            "king_over_jack": round(alpha["king_over_jack"], 4),
        },
        "strategy": _strategy_dict(tree, solver.solution_tree(), KUHN_ACTIONS),
    }


def export_leduc(iters):
    game = LeducPoker()
    tree = GameTree(game)
    solver = cfr_plus(game, tree=tree)
    solver.iterate(iters)
    return {
        "game": "leduc",
        "meta": {
            "iters": iters,
            "infosets": tree.num_infosets,
            "nodes": len(tree.nodes),
            "exploitability": float(f"{tree_exploitability(tree, solver.solution_tree()):.3e}"),
        },
        "strategy": _strategy_dict(tree, solver.solution_tree(), LEDUC_ACTIONS),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kuhn-iters", type=int, default=8000)
    ap.add_argument("--leduc-iters", type=int, default=8000)
    args = ap.parse_args()

    os.makedirs(os.path.join(WEB, "data"), exist_ok=True)
    os.makedirs(os.path.join(WEB, "assets"), exist_ok=True)

    print(f"solving Kuhn ({args.kuhn_iters} iters)...")
    kuhn = export_kuhn(args.kuhn_iters)
    print(f"  exploitability {kuhn['meta']['exploitability']:.1e}")
    print(f"solving Leduc ({args.leduc_iters} iters)...")
    leduc = export_leduc(args.leduc_iters)
    print(f"  exploitability {leduc['meta']['exploitability']:.1e}")

    with open(os.path.join(WEB, "data", "kuhn.json"), "w") as f:
        json.dump(kuhn, f, indent=1)
    with open(os.path.join(WEB, "data", "leduc.json"), "w") as f:
        json.dump(leduc, f, indent=1)

    for fig in ("kuhn_convergence.png", "leduc_convergence.png"):
        src = os.path.join(ROOT, "figures", fig)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(WEB, "assets", fig))

    print(f"wrote {WEB}/data/*.json and assets/*.png")


if __name__ == "__main__":
    main()
