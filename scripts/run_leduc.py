"""Solve Leduc Hold'em with CFR+ and report exploitability."""

import _bootstrap  # noqa: F401

import argparse
import time

from cfr_poker.best_response import tree_exploitability
from cfr_poker.cfr import cfr_plus, vanilla_cfr
from cfr_poker.games import LeducPoker
from cfr_poker.tree import GameTree


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=5000)
    ap.add_argument("--algo", choices=["cfr", "cfr+"], default="cfr+")
    args = ap.parse_args()

    game = LeducPoker()
    tree = GameTree(game)
    solver = (vanilla_cfr if args.algo == "cfr" else cfr_plus)(game, tree=tree)

    t0 = time.time()
    solver.iterate(args.iters)
    dt = time.time() - t0

    expl = tree_exploitability(tree, solver.solution_tree())
    print(f"Leduc Hold'em -- {args.algo.upper()}, {args.iters} iterations")
    print(f"  info sets       : {tree.num_infosets} (expected 288)")
    print(f"  tree nodes      : {len(tree.nodes)}")
    print(f"  exploitability  : {expl:.3e} chips/game")
    print(f"  wall clock      : {dt:.1f}s ({1000 * dt / args.iters:.1f} ms/iter)")


if __name__ == "__main__":
    main()
