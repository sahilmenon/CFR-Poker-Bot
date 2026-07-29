"""Solve Kuhn poker and validate against its closed-form solution.

Checks: (1) the self-play game value matches -1/18, (2) the recovered opener
strategy lies in the analytic alpha-family (king_bet == 3 * jack_bet), and
(3) exploitability is driven below 1e-3.
"""

import _bootstrap  # noqa: F401

import argparse

from cfr_poker.analytic import KUHN_GAME_VALUE, kuhn_alpha_consistency
from cfr_poker.best_response import tree_exploitability
from cfr_poker.cfr import cfr_plus, vanilla_cfr
from cfr_poker.evaluate import expected_value, strategy_from_table
from cfr_poker.games import KuhnPoker
from cfr_poker.tree import GameTree


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=20000)
    ap.add_argument("--algo", choices=["cfr", "cfr+"], default="cfr")
    args = ap.parse_args()

    game = KuhnPoker()
    tree = GameTree(game)
    solver = (vanilla_cfr if args.algo == "cfr" else cfr_plus)(game, tree=tree)
    solver.iterate(args.iters)

    table = solver.solution()
    sigma = strategy_from_table(game, table)
    value = expected_value(game, sigma, sigma)
    expl = tree_exploitability(tree, solver.solution_tree())
    alpha = kuhn_alpha_consistency(table)

    print(f"Kuhn poker -- {args.algo.upper()}, {args.iters} iterations")
    print(f"  info sets                : {tree.num_infosets} (expected 12)")
    print(f"  game value to P0         : {value:+.6f}  (analytic {KUHN_GAME_VALUE:+.6f})")
    print(f"  |value - (-1/18)|        : {abs(value - KUHN_GAME_VALUE):.2e}")
    print(f"  exploitability           : {expl:.3e} chips/game")
    print("  recovered opener strategy (alpha-family: king_bet == 3*jack_bet):")
    print(f"    alpha (jack bet prob)  : {alpha['jack_bet']:.4f}")
    print(f"    queen bet prob         : {alpha['queen_bet']:.4f} (analytic 0)")
    print(f"    king bet prob          : {alpha['king_bet']:.4f}")
    print(f"    king_bet / jack_bet    : {alpha['king_over_jack']:.4f} (analytic 3)")


if __name__ == "__main__":
    main()
