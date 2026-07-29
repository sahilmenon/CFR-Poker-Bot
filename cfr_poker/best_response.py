"""Best-response and exploitability -- the check most hobby CFR repos skip.

Given a strategy profile ``sigma``, a *best response* for a player is the
strategy that maximizes that player's expected payoff while the opponent keeps
playing ``sigma``. Crucially, a best response must commit a single action per
information set (it cannot peek at the hidden cards), so we cannot just take the
per-history argmax -- that would be clairvoyant and overestimate.

The algorithm (run over the compiled ``GameTree``):
  1. Forward pass: for the best-responding player, collect every decision node
     grouped by info-set id, each weighted by the *opponent + chance* reach
     probability (the responder's own probability is excluded).
  2. For each info set, choose the action maximizing the reach-weighted value,
     resolving deeper info sets first via memoized recursion.

Exploitability of ``sigma`` is ``(BR_value_0 + BR_value_1) / 2`` where
``BR_value_i`` is the value to player i of best-responding. It is >= 0 for any
profile and equals 0 exactly at a Nash equilibrium.
"""

from __future__ import annotations

from collections import defaultdict

from .games.base import Game
from .tree import TERMINAL, CHANCE, GameTree


class BestResponse:
    def __init__(self, tree: GameTree, sigma: list):
        """``sigma`` is a tree strategy: list indexed by iset of prob arrays."""
        self.tree = tree
        self.sigma = sigma

    def value(self, br_player: int) -> float:
        """Value to ``br_player`` of best-responding while the opponent plays sigma."""
        self.br_player = br_player
        self._iset_nodes = defaultdict(list)   # iset -> [(node_idx, opp_reach)]
        self._collect(self.tree.root, 1.0)
        self._best_action: dict = {}
        self._value_cache: dict = {}
        return self._value(self.tree.root)

    def _collect(self, idx, reach_opp):
        node = self.tree.nodes[idx]
        kind = node[0]
        if kind == TERMINAL:
            return
        if kind == CHANCE:
            for prob, child in node[1]:
                self._collect(child, reach_opp * prob)
            return
        _, player, iset, children = node
        if player == self.br_player:
            self._iset_nodes[iset].append((idx, reach_opp))
            for child in children:
                self._collect(child, reach_opp)  # responder's own prob excluded
        else:
            probs = self.sigma[iset]
            for i, child in enumerate(children):
                if probs[i] != 0.0:
                    self._collect(child, reach_opp * probs[i])

    def _br_action(self, iset) -> int:
        cached = self._best_action.get(iset)
        if cached is not None:
            return cached
        nodes = self.tree.nodes
        n_children = len(self.tree.iset_actions[iset])
        totals = [0.0] * n_children
        for node_idx, weight in self._iset_nodes[iset]:
            children = nodes[node_idx][3]
            for i in range(n_children):
                totals[i] += weight * self._value(children[i])
        best = max(range(n_children), key=lambda i: totals[i])
        self._best_action[iset] = best
        return best

    def _value(self, idx):
        cached = self._value_cache.get(idx)
        if cached is not None:
            return cached
        node = self.tree.nodes[idx]
        kind = node[0]
        if kind == TERMINAL:
            v = node[1] if self.br_player == 0 else -node[1]
            self._value_cache[idx] = v
            return v
        if kind == CHANCE:
            v = sum(prob * self._value(child) for prob, child in node[1])
            self._value_cache[idx] = v
            return v
        _, player, iset, children = node
        if player == self.br_player:
            v = self._value(children[self._br_action(iset)])
        else:
            probs = self.sigma[iset]
            v = 0.0
            for i, child in enumerate(children):
                if probs[i] != 0.0:
                    v += probs[i] * self._value(child)
        self._value_cache[idx] = v
        return v


def tree_exploitability(tree: GameTree, sigma: list) -> float:
    """(BR_0 + BR_1) / 2 in chips per game; 0 at a Nash equilibrium."""
    br = BestResponse(tree, sigma)
    return (br.value(0) + br.value(1)) / 2.0


def exploitability(game_or_tree, sigma) -> float:
    """Convenience wrapper.

    Accepts either a ``GameTree`` + tree strategy, or a ``Game`` + a
    ``{info_set_key: global-action prob array}`` table (builds the tree).
    """
    if isinstance(game_or_tree, GameTree):
        return tree_exploitability(game_or_tree, sigma)
    tree = GameTree(game_or_tree)
    return tree_exploitability(tree, tree.strategy_from_table(sigma))
