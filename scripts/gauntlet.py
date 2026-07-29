"""Pit the solved (near-Nash) strategy against fixed baselines.

Reports the edge in bb/100 both exactly (tree walk) and by Monte Carlo with a
95% confidence interval, seated in both positions to remove positional bias.
The exact value should sit inside the Monte Carlo interval -- a cross-check that
the simulator and the solver agree.
"""

import _bootstrap  # noqa: F401

import argparse

from cfr_poker.baselines import BASELINES, exact_bb_per_100, monte_carlo_bb_per_100
from cfr_poker.cfr import cfr_plus
from cfr_poker.evaluate import strategy_from_table
from cfr_poker.games import KuhnPoker, LeducPoker
from cfr_poker.tree import GameTree

GAMES = {"kuhn": KuhnPoker, "leduc": LeducPoker}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", choices=list(GAMES), default="leduc")
    ap.add_argument("--iters", type=int, default=4000)
    ap.add_argument("--hands", type=int, default=100_000)
    args = ap.parse_args()

    game = GAMES[args.game]()
    tree = GameTree(game)
    solver = cfr_plus(game, tree=tree)
    solver.iterate(args.iters)
    hero = strategy_from_table(game, solver.solution())

    print(f"{game.name.title()} -- solved strategy (CFR+, {args.iters} iters) "
          f"vs baselines, {args.hands} hands each")
    print(f"{'baseline':>14} | {'exact bb/100':>13} | {'monte carlo bb/100 (95% CI)':>30}")
    print("-" * 64)
    for name, make in BASELINES.items():
        villain = make(game)
        exact = exact_bb_per_100(game, hero, villain)
        mc, ci = monte_carlo_bb_per_100(game, hero, villain, hands=args.hands, seed=1)
        print(f"{name:>14} | {exact:>+13.2f} | {mc:>+18.2f}  +/- {ci:>6.2f}")


if __name__ == "__main__":
    main()
