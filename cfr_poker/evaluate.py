"""Expected-value helper: play two strategies against each other exactly.

``expected_value`` walks the whole tree and returns player 0's expected payoff
when player 0 plays ``sigma0`` and player 1 plays ``sigma1``. A strategy is a
callable ``state -> action_probability_array`` (length ``game.num_actions``),
which covers both solved (info-set-keyed) strategies and fixed baselines.
"""

from __future__ import annotations

import numpy as np

from .games.base import Game


def strategy_from_table(game: Game, table: dict):
    """Adapt an info-set-keyed dict of action distributions to a state policy."""
    def policy(state):
        key = game.infoset_key(state)
        probs = table.get(key)
        if probs is None:
            legal = game.legal_actions(state)
            probs = np.zeros(game.num_actions)
            probs[legal] = 1.0 / len(legal)
        return probs
    return policy


def expected_value(game: Game, sigma0, sigma1) -> float:
    """Player 0's exact expected utility when P0~sigma0, P1~sigma1."""
    policies = (sigma0, sigma1)

    def rec(state):
        if game.is_terminal(state):
            return game.terminal_utility(state)
        if game.is_chance(state):
            return sum(p * rec(game.apply_action(state, a))
                       for a, p in game.chance_outcomes(state))
        player = game.current_player(state)
        probs = policies[player](state)
        value = 0.0
        for a in game.legal_actions(state):
            if probs[a] != 0.0:
                value += probs[a] * rec(game.apply_action(state, a))
        return value

    return rec(game.initial_state())
