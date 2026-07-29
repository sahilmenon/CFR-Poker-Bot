"""Solver correctness: ground-truth validation and best-response sanity."""

import numpy as np
import pytest

from cfr_poker.analytic import KUHN_GAME_VALUE, kuhn_alpha_consistency
from cfr_poker.best_response import tree_exploitability
from cfr_poker.cfr import cfr_plus, vanilla_cfr
from cfr_poker.evaluate import expected_value, strategy_from_table
from cfr_poker.games import KuhnPoker, LeducPoker
from cfr_poker.games.kuhn import BET, PASS
from cfr_poker.tree import GameTree


# ---- best-response is exact on the analytic Kuhn equilibrium ----------------
def _dist(bet_prob):
    a = np.zeros(2)
    a[BET] = bet_prob
    a[PASS] = 1.0 - bet_prob
    return a


def test_best_response_exact_on_analytic_nash():
    """A hand-built Kuhn Nash equilibrium must have ~0 exploitability."""
    game = KuhnPoker()
    tree = GameTree(game)
    alpha = 1.0 / 3.0
    table = {
        "J:": _dist(alpha), "Q:": _dist(0.0), "K:": _dist(3 * alpha),
        "J:p": _dist(1 / 3), "Q:p": _dist(0.0), "K:p": _dist(1.0),
        "J:b": _dist(0.0), "Q:b": _dist(1 / 3), "K:b": _dist(1.0),
        "J:pb": _dist(0.0), "Q:pb": _dist(alpha + 1 / 3), "K:pb": _dist(1.0),
    }
    sigma = tree.strategy_from_table(table)
    assert tree_exploitability(tree, sigma) < 1e-9


# ---- Kuhn: converge to the closed-form solution -----------------------------
def test_kuhn_value_matches_minus_one_eighteenth():
    game = KuhnPoker()
    solver = vanilla_cfr(game)
    solver.iterate(8000)
    sigma = strategy_from_table(game, solver.solution())
    value = expected_value(game, sigma, sigma)
    assert abs(value - KUHN_GAME_VALUE) < 1e-3


def test_kuhn_recovers_alpha_family():
    game = KuhnPoker()
    solver = vanilla_cfr(game)
    solver.iterate(8000)
    info = kuhn_alpha_consistency(solver.solution())
    assert info["queen_bet"] < 0.02              # opener never bets the Queen
    assert abs(info["king_over_jack"] - 3.0) < 0.15  # king_bet == 3 * jack_bet


def test_kuhn_cfr_plus_drives_exploitability_below_1e_3():
    game = KuhnPoker()
    tree = GameTree(game)
    solver = cfr_plus(game, tree=tree)
    solver.iterate(5000)
    assert tree_exploitability(tree, solver.solution_tree()) < 1e-3


# ---- Leduc: structure and CFR+ improvement ----------------------------------
def test_leduc_cfr_plus_reduces_exploitability():
    game = LeducPoker()
    tree = GameTree(game)
    solver = cfr_plus(game, tree=tree)
    start = tree_exploitability(tree, solver.solution_tree())
    solver.iterate(400)
    end = tree_exploitability(tree, solver.solution_tree())
    assert end < 0.03
    assert end < start / 5


def test_cfr_plus_beats_vanilla_at_equal_iterations():
    """CFR+'s canonical output should be less exploitable than CFR's at the
    same iteration budget on Leduc."""
    game = LeducPoker()
    tree = GameTree(game)
    van = vanilla_cfr(game, tree=tree)
    plus = cfr_plus(game, tree=tree)
    van.iterate(500)
    plus.iterate(500)
    e_van = tree_exploitability(tree, van.solution_tree())
    e_plus = tree_exploitability(tree, plus.solution_tree())
    assert e_plus < e_van


@pytest.mark.parametrize("game_cls", [KuhnPoker, LeducPoker])
def test_exploitability_is_nonnegative(game_cls):
    game = game_cls()
    tree = GameTree(game)
    solver = cfr_plus(game, tree=tree)
    solver.iterate(50)
    assert tree_exploitability(tree, solver.solution_tree()) >= -1e-12
