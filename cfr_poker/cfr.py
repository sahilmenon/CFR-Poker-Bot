"""Counterfactual Regret Minimization -- vanilla CFR and CFR+.

A single game-agnostic solver that walks the full game tree each iteration.
Utilities are tracked in **player 0's frame** and the sign is flipped for the
acting player, so the same traversal is correct for games with chance nodes and
non-strictly-alternating turns (e.g. Leduc's board reveal between rounds).

  * Vanilla CFR (Zinkevich et al. 2007): regret matching, simultaneous updates,
    uniformly averaged strategy.
  * CFR+ (Tammelin 2014): regret-matching+ (regrets clamped at 0), alternating
    player updates, and linear (iteration-weighted) strategy averaging.

The solver runs over a compiled ``GameTree`` (see ``tree.py``). Regrets and
strategy sums are kept as plain Python lists of floats: for the 2-3 action
info sets in these games that is markedly faster than NumPy per-node, so Leduc
converges in a fraction of a second per iteration.
"""

from __future__ import annotations

import numpy as np

from .games.base import Game
from .tree import TERMINAL, CHANCE, GameTree


def _regret_matching(regret: list) -> list:
    pos = [r if r > 0.0 else 0.0 for r in regret]
    total = 0.0
    for p in pos:
        total += p
    if total > 0.0:
        return [p / total for p in pos]
    u = 1.0 / len(regret)
    return [u] * len(regret)


def regret_matching(regret) -> np.ndarray:
    """Public helper: regret matching as a NumPy array."""
    return np.asarray(_regret_matching(list(regret)))


class CFRSolver:
    def __init__(self, game: Game, *, plus: bool = False,
                 linear: bool = False, alternating: bool = False,
                 tree: GameTree | None = None):
        self.game = game
        self.tree = tree if tree is not None else GameTree(game)
        self.plus = plus
        self.linear = linear
        self.alternating = alternating
        self.regret = [[0.0] * len(a) for a in self.tree.iset_actions]
        self.strategy_sum = [[0.0] * len(a) for a in self.tree.iset_actions]
        self.iterations = 0

    # ---- one traversal (returns value to player 0) ---------------------------
    def _traverse(self, idx, reach0, reach1, reachc, update_player, t):
        node = self.tree.nodes[idx]
        kind = node[0]
        if kind == TERMINAL:
            return node[1]
        if kind == CHANCE:
            value = 0.0
            for prob, child in node[1]:
                value += prob * self._traverse(
                    child, reach0, reach1, reachc * prob, update_player, t
                )
            return value

        _, player, iset, children = node
        strat = _regret_matching(self.regret[iset])
        util = [0.0] * len(children)
        node_value = 0.0
        if player == 0:
            for i, child in enumerate(children):
                u = self._traverse(child, reach0 * strat[i], reach1, reachc,
                                   update_player, t)
                util[i] = u
                node_value += strat[i] * u
        else:
            for i, child in enumerate(children):
                u = self._traverse(child, reach0, reach1 * strat[i], reachc,
                                   update_player, t)
                util[i] = u
                node_value += strat[i] * u

        if update_player is None or player == update_player:
            regret = self.regret[iset]
            ssum = self.strategy_sum[iset]
            if player == 0:
                cf_reach = reach1 * reachc
                own_reach = reach0
                sign = 1.0
            else:
                cf_reach = reach0 * reachc
                own_reach = reach1
                sign = -1.0
            weight = own_reach * (t if self.linear else 1.0)
            if self.plus:
                for i in range(len(children)):
                    r = regret[i] + cf_reach * sign * (util[i] - node_value)
                    regret[i] = r if r > 0.0 else 0.0
                    ssum[i] += weight * strat[i]
            else:
                for i in range(len(children)):
                    regret[i] += cf_reach * sign * (util[i] - node_value)
                    ssum[i] += weight * strat[i]

        return node_value

    # ---- driving iterations --------------------------------------------------
    def iterate(self, n: int = 1):
        root = self.tree.root
        for _ in range(n):
            self.iterations += 1
            t = self.iterations
            if self.alternating:
                self._traverse(root, 1.0, 1.0, 1.0, 0, t)
                self._traverse(root, 1.0, 1.0, 1.0, 1, t)
            else:
                self._traverse(root, 1.0, 1.0, 1.0, None, t)

    # ---- strategy read-out ---------------------------------------------------
    def average_strategy_tree(self) -> list:
        strat = []
        for ssum in self.strategy_sum:
            total = sum(ssum)
            if total > 0.0:
                strat.append([s / total for s in ssum])
            else:
                strat.append([1.0 / len(ssum)] * len(ssum))
        return strat

    def current_strategy_tree(self) -> list:
        return [_regret_matching(r) for r in self.regret]

    def average_strategy(self) -> dict:
        """Average strategy as ``{info_set_key: global-action prob array}``."""
        return self.tree.strategy_to_table(self.average_strategy_tree())

    def current_strategy(self) -> dict:
        return self.tree.strategy_to_table(self.current_strategy_tree())

    def solution_tree(self) -> list:
        """The strategy each algorithm is designed to output.

        Vanilla CFR converges only in its *average* strategy (the current
        strategy oscillates). CFR+ converges in its *current* strategy
        (Tammelin 2014, Theorem 2) -- averaging is unnecessary and, with the
        wild pure strategies RM+ produces early on, would only slow it down.
        """
        return self.current_strategy_tree() if self.plus else self.average_strategy_tree()

    def solution(self) -> dict:
        return self.tree.strategy_to_table(self.solution_tree())


def vanilla_cfr(game: Game, tree: GameTree | None = None) -> CFRSolver:
    return CFRSolver(game, plus=False, linear=False, alternating=False, tree=tree)


def cfr_plus(game: Game, tree: GameTree | None = None) -> CFRSolver:
    return CFRSolver(game, plus=True, linear=True, alternating=True, tree=tree)
