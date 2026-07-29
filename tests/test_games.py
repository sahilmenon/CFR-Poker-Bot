"""Structural tests for the game engines (independent of any solver)."""

import numpy as np

from cfr_poker.games import KuhnPoker, LeducPoker
from cfr_poker.tree import GameTree


def _walk_terminal_utilities(game):
    """Collect (chance-weighted) reachable terminal utilities under uniform play."""
    utils = []

    def rec(state, prob):
        if game.is_terminal(state):
            utils.append((prob, game.terminal_utility(state)))
            return
        if game.is_chance(state):
            for a, p in game.chance_outcomes(state):
                rec(game.apply_action(state, a), prob * p)
            return
        legal = game.legal_actions(state)
        for a in legal:
            rec(game.apply_action(state, a), prob / len(legal))

    rec(game.initial_state(), 1.0)
    return utils


def test_kuhn_has_12_infosets():
    tree = GameTree(KuhnPoker())
    assert tree.num_infosets == 12


def test_kuhn_zero_sum_and_bounded():
    game = KuhnPoker()
    for _, u in _walk_terminal_utilities(game):
        assert abs(u) in (1.0, 2.0)


def test_kuhn_chance_is_uniform_over_six_deals():
    game = KuhnPoker()
    outcomes = game.chance_outcomes(game.initial_state())
    assert len(outcomes) == 6
    assert np.isclose(sum(p for _, p in outcomes), 1.0)


def test_leduc_has_288_infosets():
    tree = GameTree(LeducPoker())
    assert tree.num_infosets == 288


def test_leduc_chance_probabilities_sum_to_one():
    game = LeducPoker()
    root = game.initial_state()
    assert np.isclose(sum(p for _, p in game.chance_outcomes(root)), 1.0)
    # After a deal, the board reveal is over the 4 remaining cards.
    dealt = game.apply_action(root, 0)
    # Advance through a check-check round to reach the board-reveal chance node.
    from cfr_poker.games.leduc import CALL
    s = game.apply_action(dealt, CALL)
    s = game.apply_action(s, CALL)
    assert game.is_chance(s)
    board = game.chance_outcomes(s)
    assert len(board) == 4
    assert np.isclose(sum(p for _, p in board), 1.0)


def test_leduc_pair_beats_high_card():
    game = LeducPoker()
    # Construct a showdown: P0 holds a King(id 4), P1 holds a King(id 5),
    # board is a Jack(id 0) -> no pair, tie on Kings -> split.
    from cfr_poker.games.leduc import LeducState
    s = LeducState(private=(4, 5), board=0, rnd=1, history=(1, 1),
                   r0_history=(1, 1), committed=(1, 1), terminal=True)
    assert game.terminal_utility(s) == 0.0
    # Now P0 pairs the board (board King id 1), P1 holds a Jack.
    s2 = LeducState(private=(4, 0), board=5, rnd=1, history=(1, 1),
                    r0_history=(1, 1), committed=(3, 3), terminal=True)
    assert game.terminal_utility(s2) == 3.0  # P0 wins P1's contribution
