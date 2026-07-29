"""Fixed baseline opponents and the exact/Monte-Carlo gauntlet.

Baselines are simple, well-known non-adaptive strategies:
  * ``random``      -- uniform over legal actions.
  * ``call_station``-- never folds, never raises (check/call only).
  * ``always_raise``-- raises/bets whenever legal, otherwise calls.

A solved Nash strategy should beat all three. We measure the edge in bb/100
(chips per 100 hands), computed two ways: exactly via a tree walk, and by Monte
Carlo with a 95% confidence interval to mirror the "100k hands" resume bullet.
"""

from __future__ import annotations

import numpy as np

from .evaluate import expected_value
from .games.base import Game
from .games.leduc import FOLD, CALL, RAISE


# ---- baseline policies (state -> action-probability array) ------------------
def random_policy(game: Game):
    def policy(state):
        legal = game.legal_actions(state)
        probs = np.zeros(game.num_actions)
        probs[legal] = 1.0 / len(legal)
        return probs
    return policy


def _deterministic(game: Game, pick):
    def policy(state):
        legal = game.legal_actions(state)
        probs = np.zeros(game.num_actions)
        probs[pick(legal)] = 1.0
        return probs
    return policy


# Action ids are ordered by aggression (FOLD < CALL/check < RAISE/bet). The
# aggressive action is always the highest legal id. The passive action is the
# lowest legal id -- except when facing a bet, where the lowest id is FOLD, so a
# call station excludes it. is_facing_bet lets this stay correct even in Kuhn,
# whose single PASS action doubles as both fold and check.
def call_station_policy(game: Game):
    """Never folds, never raises: checks when able, calls any bet."""
    def pick(game, state):
        legal = game.legal_actions(state)
        if game.is_facing_bet(state):
            legal = [a for a in legal if a != FOLD]
        return min(legal)
    return lambda state: _one_hot(game, pick(game, state))


def always_raise_policy(game: Game):
    """Maximal aggression: raises/bets when able, else calls (never folds)."""
    return _deterministic(game, lambda legal: max(legal))


def _one_hot(game: Game, action: int):
    probs = np.zeros(game.num_actions)
    probs[action] = 1.0
    return probs


BASELINES = {
    "random": random_policy,
    "call_station": call_station_policy,
    "always_raise": always_raise_policy,
}


# ---- exact head-to-head -----------------------------------------------------
def exact_bb_per_100(game: Game, hero, villain) -> float:
    """Hero's exact expected chips per 100 hands, averaged over both seats."""
    as_p0 = expected_value(game, hero, villain)          # hero is player 0
    as_p1 = -expected_value(game, villain, hero)          # hero is player 1
    return 100.0 * 0.5 * (as_p0 + as_p1)


# ---- Monte Carlo with a confidence interval ---------------------------------
def _play_hand(game: Game, policies, rng) -> float:
    state = game.initial_state()
    while not game.is_terminal(state):
        if game.is_chance(state):
            outcomes = game.chance_outcomes(state)
            actions = [a for a, _ in outcomes]
            probs = [p for _, p in outcomes]
            action = actions[rng.choice(len(actions), p=probs)]
        else:
            player = game.current_player(state)
            probs = policies[player](state)
            legal = game.legal_actions(state)
            p = np.array([probs[a] for a in legal], dtype=float)
            p /= p.sum()
            action = legal[rng.choice(len(legal), p=p)]
        state = game.apply_action(state, action)
    return game.terminal_utility(state)


def monte_carlo_bb_per_100(game: Game, hero, villain, hands: int = 100_000, seed: int = 0):
    """Simulate ``hands`` (split across both seats); return (bb/100, ci95)."""
    rng = np.random.default_rng(seed)
    half = hands // 2
    # Hero as player 0.
    r0 = np.array([_play_hand(game, (hero, villain), rng) for _ in range(half)])
    # Hero as player 1 (negate: payoffs are reported for player 0).
    r1 = np.array([-_play_hand(game, (villain, hero), rng) for _ in range(half)])
    results = np.concatenate([r0, r1])
    mean = results.mean()
    stderr = results.std(ddof=1) / np.sqrt(len(results))
    return 100.0 * mean, 100.0 * 1.96 * stderr
