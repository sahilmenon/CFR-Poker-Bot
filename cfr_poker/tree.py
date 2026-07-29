"""Compile a Game into a flat node array for fast CFR and best-response.

Walking the abstract ``Game`` interface (creating immutable states, rebuilding
info-set keys) every iteration is fine for Kuhn but far too slow for Leduc. We
therefore expand the game once into a tree of lightweight nodes that share
information-set ids, and run all inner loops over that tree with no further
calls into the game.

Node encodings (tuples, tagged by an int kind):
  * terminal:  ``(0, utility_to_player0)``
  * chance:    ``(1, [(prob, child_idx), ...])``
  * decision:  ``(2, player, iset_id, [child_idx, ...])``  children align with
               ``iset_actions[iset_id]`` (the global action ids at that info set).

A *strategy* on a tree is a list indexed by ``iset_id`` of probability arrays,
each aligned with that info set's local action ordering.
"""

from __future__ import annotations

import numpy as np

from .games.base import Game

TERMINAL, CHANCE, DECISION = 0, 1, 2


class GameTree:
    def __init__(self, game: Game):
        self.game = game
        self.nodes: list = []
        self.iset_key: list = []      # iset_id -> info-set key (str)
        self.iset_actions: list = []  # iset_id -> list of global action ids
        self.iset_player: list = []   # iset_id -> acting player
        self._iset_ids: dict = {}
        self.root = self._build(game.initial_state())

    def _build(self, state) -> int:
        g = self.game
        if g.is_terminal(state):
            self.nodes.append((TERMINAL, g.terminal_utility(state)))
            return len(self.nodes) - 1
        if g.is_chance(state):
            children = [(prob, self._build(g.apply_action(state, a)))
                        for a, prob in g.chance_outcomes(state)]
            self.nodes.append((CHANCE, children))
            return len(self.nodes) - 1
        key = g.infoset_key(state)
        actions = list(g.legal_actions(state))
        iset = self._iset_ids.get(key)
        if iset is None:
            iset = len(self.iset_key)
            self._iset_ids[key] = iset
            self.iset_key.append(key)
            self.iset_actions.append(actions)
            self.iset_player.append(g.current_player(state))
        children = [self._build(g.apply_action(state, a)) for a in actions]
        self.nodes.append((DECISION, g.current_player(state), iset, children))
        return len(self.nodes) - 1

    @property
    def num_infosets(self) -> int:
        return len(self.iset_key)

    # ---- strategy helpers ----------------------------------------------------
    def uniform_strategy(self) -> list:
        return [np.full(len(a), 1.0 / len(a)) for a in self.iset_actions]

    def strategy_from_table(self, table: dict) -> list:
        """Convert a ``{info_set_key: global-action prob array}`` table to a
        tree strategy (per-iset arrays aligned to local action ordering)."""
        strat = []
        for iset, actions in enumerate(self.iset_actions):
            probs = table.get(self.iset_key[iset])
            if probs is None:
                strat.append(np.full(len(actions), 1.0 / len(actions)))
                continue
            local = np.array([probs[a] for a in actions], dtype=float)
            total = local.sum()
            strat.append(local / total if total > 0 else
                         np.full(len(actions), 1.0 / len(actions)))
        return strat

    def strategy_to_table(self, strat: list) -> dict:
        """Inverse: per-iset local arrays -> ``{key: global-action prob array}``."""
        table = {}
        for iset, actions in enumerate(self.iset_actions):
            full = np.zeros(self.game.num_actions)
            full[actions] = strat[iset]
            table[self.iset_key[iset]] = full
        return table
